"""SS-DST (State-Space Dialogue State Tracking) meeting recap method.

Research contribution: the baseline ``HierarchicalRecapMethod`` summarizes each
8-utterance chunk in *isolation* (parallel, no shared memory between chunks).
This causes three failure modes on real meeting transcripts:

1. **Coreference loss** — pronouns / deictic references ("nó", "vấn đề đó",
   "pipeline mới") that resolve to entities introduced in an earlier chunk are
   left dangling, producing incomplete or ambiguous notes.
2. **Decision fragmentation** — a decision reached incrementally across chunks
   2, 3 and 5 is split into disjoint, locally-incomplete notes.
3. **No rolling memory** — entities, decisions and open action items established
   earlier in the chapter are invisible to later chunks.

SS-DST maintains a rolling **dialogue belief state** ``s_t`` — a compact JSON
memory — that is (a) *injected* into each chunk's prompt as prior context and
(b) *updated* after each chunk summary via a dedicated state-update LLM call.
This mirrors Dialogue State Tracking (track slots/beliefs across turns) and the
state-space recurrence of SSMs/Mamba (``s_t = Update(s_{t-1}, x_t)``), realized
at the prompt/LLM level for meeting summarization.

State update equation (conceptual)::

    s_t = Update(s_{t-1}, summary(x_t), x_t)

where ``s_t`` is a bounded belief state::

    {current_topic, entities, decisions, open_actions, resolved_references}

Trade-off vs. baseline: chunks within a chapter are processed **sequentially**
(state depends on order) instead of in parallel, so wall-clock per chapter is
higher but coherence / coreference resolution improves. The state is bounded
(~180 tokens) with an explicit "forgetting gate" to control prompt growth.
"""

import json
from typing import Any

from app.services.completion_client import (
    JsonCompletionRunner,
    complete_json_with_target_fallback,
    normalized_model_runs,
)
from app.services.llm_output_schemas import is_valid_chunk_note_item
from app.services.model_targets import ModelTarget, model_stage_max_workers
from app.services.parallel import parallel_map_ordered
from app.services.prompt_loader import PromptLoader
from app.services.text_utils import clean_text, estimate_tokens
from app.services.transcript_parser import Utterance, utterance_to_dict

from app.methods.hierarchical_recap import (
    LOCAL_NOTE_MAX_TOKENS,
    LOCAL_TITLE_MAX_TOKENS,
    build_timespan,
    chunk_segment,
    deduplicate_note_records,
    fallback_chunk_summary,
    fallback_title_result,
    has_complete_chunk_note_result,
    is_valid_title_result,
    parse_title_result,
    render_chunks,
    segment_utterances_texttiling,
)


SSDST_STATE_MAX_TOKENS = 384
EMPTY_BELIEF_STATE: dict[str, Any] = {
    "current_topic": "",
    "entities": [],
    "decisions": [],
    "open_actions": [],
    "resolved_references": [],
}


class SsDstRecapMethod:
    name = "ssdst"

    def summarize(
        self,
        utterances: list[Utterance],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        input_name: str,
    ) -> dict[str, Any]:
        segments, segmentation_trace = segment_utterances_texttiling(utterances)
        chapters: list[dict[str, Any]] = []
        model_runs: list[dict[str, Any]] = []
        chapter_jobs: list[dict[str, Any]] = []
        for chapter_number, segment in enumerate(segments, start=1):
            segment_utterances = segment["utterances"]
            chapter_jobs.append(
                {
                    "chapter_number": chapter_number,
                    "segment_utterances": segment_utterances,
                    "chunks": chunk_segment(segment_utterances),
                    "title_offset": (chapter_number - 1) * 2,
                }
            )

        # Title stage runs in parallel across chapters (titles are independent of state).
        title_runs_by_chapter: dict[int, list[dict[str, Any]]] = {}
        note_runs_by_chapter: dict[int, list[dict[str, Any]]] = {}
        state_runs_by_chapter: dict[int, list[dict[str, Any]]] = {}
        state_trace_by_chapter: dict[int, list[dict[str, Any]]] = {}

        def run_title(job: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
            chapter_number = job["chapter_number"]
            runs = self._run_title_stage(
                input_name,
                chapter_number,
                job["segment_utterances"],
                runner,
                targets,
                job["title_offset"],
            )
            return chapter_number, runs

        for chapter_number, runs in parallel_map_ordered(
            chapter_jobs, run_title, max_workers=model_stage_max_workers(targets)
        ):
            title_runs_by_chapter[chapter_number] = runs

        # Note + state stage: SEQUENTIAL within a chapter (state depends on order),
        # but chapters can still advance in parallel because each chapter keeps its
        # own independent belief state.
        def run_chapter_notes(job: dict[str, Any]) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
            chapter_number = job["chapter_number"]
            chunks = job["chunks"]
            note_runs, state_runs, state_trace = self._run_sequential_note_stage(
                input_name, chapter_number, chunks, runner, targets
            )
            return chapter_number, note_runs, state_runs, state_trace

        for chapter_number, note_runs, state_runs, state_trace in parallel_map_ordered(
            chapter_jobs, run_chapter_notes, max_workers=model_stage_max_workers(targets)
        ):
            note_runs_by_chapter[chapter_number] = note_runs
            state_runs_by_chapter[chapter_number] = state_runs
            state_trace_by_chapter[chapter_number] = state_trace

        for job in chapter_jobs:
            chapter_number = job["chapter_number"]
            segment_utterances = job["segment_utterances"]
            chunks = job["chunks"]
            title_runs = title_runs_by_chapter.get(chapter_number, [])
            model_runs.extend(normalized_model_runs("hierarchical_title", title_runs))
            title_result = parse_title_result(title_runs, segment_utterances)

            note_runs = note_runs_by_chapter.get(chapter_number, [])
            model_runs.extend(normalized_model_runs("ssdst_abstractive", note_runs))
            state_runs = state_runs_by_chapter.get(chapter_number, [])
            model_runs.extend(normalized_model_runs("ssdst_state_update", state_runs))
            notes_by_chunk = parse_chunk_notes(note_runs, chunks)

            rendered_chunks = render_chunks(chunks, notes_by_chunk)
            chapters.append(
                {
                    "chapter_number": chapter_number,
                    "title": title_result["title"],
                    "summary": title_result["one_line_summary"],
                    "timespan": build_timespan(segment_utterances),
                    "utterance_ids": [item.index for item in segment_utterances],
                    "chunks": rendered_chunks,
                    "notes": deduplicate_note_records([note for chunk in rendered_chunks for note in chunk["notes"]]),
                    "belief_state_trace": state_trace_by_chapter.get(chapter_number, []),
                    "final_belief_state": (state_trace_by_chapter.get(chapter_number, [{}]) or [{}])[-1].get("state", dict(EMPTY_BELIEF_STATE)),
                }
            )

        return {
            "method": self.name,
            "paper_mapping": {
                "design_rationale": "SS-DST - rolling dialogue belief state across chunks for coreference resolution and decision continuity",
                "segmentation_window": "TextTiling-style 30 utterances with stride 10 (reused from hierarchical)",
                "chunking": "8-utterance chunks processed SEQUENTIALLY with state injection (vs parallel isolated in hierarchical)",
                "state_tracking": "ssdst_state_update folds each chunk into a bounded belief state {current_topic, entities, decisions, open_actions, resolved_references}",
                "title_generation": "hierarchical_title reused (titles are state-independent)",
                "ux_shape": "chronological chapters with rolling belief-state-aware notes and raw transcript context",
            },
            "chapters": chapters,
            "segmentation_trace": segmentation_trace,
            "model_runs": model_runs,
        }

    def _run_title_stage(
        self,
        input_name: str,
        chapter_number: int,
        segment_utterances: list[Utterance],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        call_offset: int,
    ) -> list[dict[str, Any]]:
        from app.methods.hierarchical_recap import build_hierarchical_title_prompt

        return complete_json_with_target_fallback(
            runner,
            "hierarchical_title",
            build_hierarchical_title_prompt(input_name, chapter_number, segment_utterances),
            targets,
            call_offset,
            max_tokens=LOCAL_TITLE_MAX_TOKENS,
            success_predicate=is_valid_title_result,
        )

    def _run_sequential_note_stage(
        self,
        input_name: str,
        chapter_number: int,
        chunks: list[dict[str, Any]],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Process chunks sequentially, threading a belief state through them.

        Returns (note_runs, state_runs, state_trace) where state_trace is the
        ordered list of {chunk_id, state} snapshots for analysis/evaluation.
        """
        note_runs: list[dict[str, Any]] = []
        state_runs: list[dict[str, Any]] = []
        state_trace: list[dict[str, Any]] = []
        belief_state: dict[str, Any] = dict(EMPTY_BELIEF_STATE)

        for chunk_index, chunk in enumerate(chunks, start=1):
            chunk_batch = [chunk]
            note_prompt = build_ssdst_abstractive_prompt(
                input_name, chapter_number, chunk_index, belief_state, chunk_batch
            )
            batch_runs = complete_json_with_target_fallback(
                runner,
                "ssdst_abstractive",
                note_prompt,
                targets,
                chunk_index,
                max_tokens=LOCAL_NOTE_MAX_TOKENS,
                success_predicate=lambda parsed, batch_chunks=chunk_batch: has_complete_chunk_note_result(parsed, batch_chunks),
                response_schema=ssdst_abstractive_schema_for_chunks(chunk_batch),
            )
            for run in batch_runs:
                run["batch_number"] = chunk_index
                run["chunk_ids"] = [chunk["chunk_id"] for chunk in chunk_batch]
            note_runs.extend(batch_runs)

            chunk_summary = extract_chunk_summary(batch_runs, chunk)
            chunk_text = format_chunk_text(chunk)

            state_prompt = build_ssdst_state_update_prompt(
                chapter_number, chunk_index, belief_state, chunk_text, chunk_summary
            )
            state_batch_runs = complete_json_with_target_fallback(
                runner,
                "ssdst_state_update",
                state_prompt,
                targets,
                chunk_index,
                max_tokens=SSDST_STATE_MAX_TOKENS,
                success_predicate=is_valid_belief_state,
                response_schema=response_schema_for_state(),
            )
            state_runs.extend(state_batch_runs)

            new_state = extract_belief_state(state_batch_runs)
            belief_state = new_state
            state_trace.append({"chunk_id": chunk["chunk_id"], "chunk_index": chunk_index, "state": belief_state})

        return note_runs, state_runs, state_trace


def build_ssdst_abstractive_prompt(
    input_name: str,
    chapter_number: int,
    chunk_index: int,
    belief_state: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> str:
    prompt_chunks = [
        {
            "chunk_id": chunk["chunk_id"],
            "utterance_ids": chunk["utterance_ids"],
            "utterances": [utterance_to_dict(item) for item in chunk["utterances"]],
        }
        for chunk in chunks
    ]
    required_chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    example_chunk_id = required_chunk_ids[0] if required_chunk_ids else "chunk-id"
    template = PromptLoader.get_prompt("ssdst_abstractive")
    return (
        template.replace("{input_name}", input_name)
        .replace("{chapter_number}", str(chapter_number))
        .replace("{chunk_index}", str(chunk_index))
        .replace("{belief_state}", json.dumps(belief_state, ensure_ascii=False, indent=2))
        .replace("{required_chunk_ids}", json.dumps(required_chunk_ids, ensure_ascii=False, indent=2))
        .replace("{prompt_chunks}", json.dumps(prompt_chunks, ensure_ascii=False, indent=2))
        .replace("{example_chunk_id}", example_chunk_id)
    )


def build_ssdst_state_update_prompt(
    chapter_number: int,
    chunk_index: int,
    previous_state: dict[str, Any],
    chunk_text: str,
    chunk_summary: str,
) -> str:
    template = PromptLoader.get_prompt("ssdst_state_update")
    return (
        template.replace("{chapter_number}", str(chapter_number))
        .replace("{chunk_index}", str(chunk_index))
        .replace("{previous_state}", json.dumps(previous_state, ensure_ascii=False, indent=2))
        .replace("{chunk_text}", chunk_text)
        .replace("{chunk_summary}", chunk_summary)
    )


def ssdst_abstractive_schema_for_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]
    notes_schema: dict[str, Any] = {
        "type": "array",
        "minItems": len(chunk_ids),
        "maxItems": len(chunk_ids),
    }
    if chunk_ids:
        notes_schema["items"] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "chunk_id": {"type": "string", "enum": chunk_ids},
                "summary": {"type": "string", "minLength": 1},
                "contains_key_point": {"type": "boolean"},
                "contains_action_item": {"type": "boolean"},
            },
            "required": ["chunk_id", "summary", "contains_key_point", "contains_action_item"],
        }
    else:
        notes_schema["items"] = {"type": "object"}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"notes": notes_schema},
        "required": ["notes"],
    }


def response_schema_for_state() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "current_topic": {"type": "string"},
            "entities": {"type": "array", "items": {"type": "string"}},
            "decisions": {"type": "array", "items": {"type": "string"}},
            "open_actions": {"type": "array", "items": {"type": "string"}},
            "resolved_references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "pronoun": {"type": "string"},
                        "refers_to": {"type": "string"},
                    },
                    "required": ["pronoun", "refers_to"],
                },
            },
        },
        "required": ["current_topic", "entities", "decisions", "open_actions", "resolved_references"],
    }


def is_valid_belief_state(parsed: Any) -> bool:
    if not isinstance(parsed, dict):
        return False
    for key in ("current_topic", "entities", "decisions", "open_actions", "resolved_references"):
        if key not in parsed:
            return False
    return True


def extract_belief_state(runs: list[dict[str, Any]]) -> dict[str, Any]:
    for run in runs:
        if run.get("error"):
            continue
        parsed = run.get("parsed")
        if isinstance(parsed, dict) and is_valid_belief_state(parsed):
            return normalize_belief_state(parsed)
    return dict(EMPTY_BELIEF_STATE)


def normalize_belief_state(parsed: dict[str, Any]) -> dict[str, Any]:
    def as_str_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [clean_text(item) for item in value if clean_text(item)]
        if isinstance(value, str) and clean_text(value):
            return [clean_text(value)]
        return []

    def as_ref_list(value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        refs: list[dict[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                pronoun = clean_text(item.get("pronoun"))
                refers_to = clean_text(item.get("refers_to"))
                if pronoun and refers_to:
                    refs.append({"pronoun": pronoun, "refers_to": refers_to})
        return refs

    return {
        "current_topic": clean_text(parsed.get("current_topic")),
        "entities": as_str_list(parsed.get("entities")),
        "decisions": as_str_list(parsed.get("decisions")),
        "open_actions": as_str_list(parsed.get("open_actions")),
        "resolved_references": as_ref_list(parsed.get("resolved_references")),
    }


def extract_chunk_summary(runs: list[dict[str, Any]], chunk: dict[str, Any]) -> str:
    for run in runs:
        if run.get("error"):
            continue
        parsed = run.get("parsed")
        if not isinstance(parsed, (dict, list)):
            continue
        for note in iter_note_items(parsed):
            summary = clean_text(note.get("summary") or note.get("note") or note.get("text"))
            if summary:
                return summary
    return fallback_chunk_summary(chunk)


def iter_note_items(parsed: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                items.append(item)
        return items
    if isinstance(parsed, dict):
        for key in ("notes", "chunks", "chunk_notes", "summaries", "items"):
            value = parsed.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        items.append(item)
    return items


def format_chunk_text(chunk: dict[str, Any]) -> str:
    utterances = chunk.get("utterances", []) or []
    return "\n".join(f"U{item.index} {item.speaker}: {item.text}" for item in utterances)


def parse_chunk_notes(runs: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Parse ssdst_abstractive runs into per-chunk notes.

    Reuses the hierarchical parser shape but is local so the SS-DST module is
    self-contained and does not depend on private helpers of hierarchical_recap
    beyond the explicitly imported public ones.
    """
    from app.methods.hierarchical_recap import (
        attach_unknown_notes_by_order,
        fill_missing_chunk_notes,
        iter_chunk_note_items,
    )

    notes_by_chunk: dict[str, list[dict[str, Any]]] = {chunk["chunk_id"]: [] for chunk in chunks}
    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    unknown_chunk_notes: list[dict[str, Any]] = []
    for run in runs:
        if run.get("error"):
            continue
        parsed = run.get("parsed")
        if not isinstance(parsed, (dict, list)):
            continue
        for note in iter_chunk_note_items(parsed, notes_by_chunk):
            chunk_id = clean_text(note.get("chunk_id"))
            target_chunk = chunks_by_id.get(chunk_id)
            if target_chunk is None and len(chunks) == 1:
                target_chunk = chunks[0]
                chunk_id = chunks[0]["chunk_id"]
            model_summary = clean_text(note.get("summary") or note.get("note") or note.get("text"))
            summary = model_summary or (fallback_chunk_summary(target_chunk) if target_chunk else "")
            normalized_note = dict(note)
            normalized_note["summary"] = summary
            if not is_valid_chunk_note_item(normalized_note):
                continue
            note_record = {
                "summary": summary,
                "contains_key_point": bool(note.get("contains_key_point")),
                "contains_action_item": bool(note.get("contains_action_item")),
                "generated_by": run.get("target", "") if model_summary else "local-fallback",
            }
            if chunk_id in notes_by_chunk:
                notes_by_chunk[chunk_id].append(note_record)
            elif len(chunks) == 1:
                notes_by_chunk[chunks[0]["chunk_id"]].append(note_record)
            else:
                unknown_chunk_notes.append(note_record)
    attach_unknown_notes_by_order(notes_by_chunk, chunks, unknown_chunk_notes)
    fill_missing_chunk_notes(notes_by_chunk, chunks)
    return notes_by_chunk
