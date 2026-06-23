import json
import statistics
from collections import Counter
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
from app.services.text_utils import clean_text, cosine_similarity, estimate_tokens, tokenize_for_similarity
from app.services.transcript_parser import Utterance, format_utterances, utterance_to_dict


WINDOW_UTTERANCES = 30
STRIDE_UTTERANCES = 10
CHUNK_UTTERANCES = 8
LOCAL_TITLE_MAX_TOKENS = 192
LOCAL_NOTE_MAX_TOKENS = 512


class HierarchicalRecapMethod:
    name = "hierarchical"

    def summarize(
        self,
        utterances: list[Utterance],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        input_name: str,
    ) -> dict[str, Any]:
        segments, segmentation_trace = segment_utterances_texttiling(utterances)
        chapters = []
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
                    "note_offset": ((chapter_number - 1) * 2) + 1,
                }
            )

        title_runs_by_chapter: dict[int, list[dict[str, Any]]] = {}
        note_runs_by_chapter: dict[int, list[dict[str, Any]]] = {}
        stage_jobs = [(stage_name, job) for job in chapter_jobs for stage_name in ("title", "note")]

        def run_stage(stage_job: tuple[str, dict[str, Any]]) -> tuple[str, int, list[dict[str, Any]]]:
            stage_name, job = stage_job
            chapter_number = job["chapter_number"]
            if stage_name == "title":
                runs = self._run_title_stage(
                    input_name,
                    chapter_number,
                    job["segment_utterances"],
                    runner,
                    targets,
                    job["title_offset"],
                )
                return stage_name, chapter_number, runs
            runs = self._run_note_stage(input_name, chapter_number, job["chunks"], runner, targets, job["note_offset"])
            return stage_name, chapter_number, runs

        for stage_name, chapter_number, runs in parallel_map_ordered(stage_jobs, run_stage, max_workers=model_stage_max_workers(targets)):
            if stage_name == "title":
                title_runs_by_chapter[chapter_number] = runs
            else:
                note_runs_by_chapter[chapter_number] = runs

        for job in chapter_jobs:
            chapter_number = job["chapter_number"]
            segment_utterances = job["segment_utterances"]
            chunks = job["chunks"]
            title_runs = title_runs_by_chapter.get(chapter_number, [])
            model_runs.extend(normalized_model_runs("hierarchical_title", title_runs))
            title_result = parse_title_result(title_runs, segment_utterances)

            note_runs = note_runs_by_chapter.get(chapter_number, [])
            model_runs.extend(normalized_model_runs("hierarchical_abstractive", note_runs))
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
                }
            )

        return {
            "method": self.name,
            "paper_mapping": {
                "design_rationale": "DR2 - summarize entire meeting in chapterized structure for detailed context and knowledge sharing",
                "segmentation_window": "hierarchical_segment substitute uses TextTiling-style 30 utterances with stride 10 utterances",
                "chunking": "hierarchical_abstractive substitute summarizes each 8-utterance chunk independently",
                "title_generation": "hierarchical_title substitute generates one title per segment",
                "ux_shape": "chronological chapters with title, one-line summary, rolling notes, and raw transcript context",
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
        return complete_json_with_target_fallback(
            runner,
            "hierarchical_title",
            build_hierarchical_title_prompt(input_name, chapter_number, segment_utterances),
            targets,
            call_offset,
            max_tokens=LOCAL_TITLE_MAX_TOKENS,
            success_predicate=is_valid_title_result,
        )

    def _run_note_stage(
        self,
        input_name: str,
        chapter_number: int,
        chunks: list[dict[str, Any]],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        call_offset: int,
    ) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        chunk_batches = list(enumerate(hierarchical_abstractive_batches(chunks), start=1))

        def run_batch(batch: tuple[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
            batch_number, chunk_batch = batch
            batch_runs = complete_json_with_target_fallback(
                runner,
                "hierarchical_abstractive",
                build_hierarchical_abstractive_prompt(input_name, chapter_number, chunk_batch),
                targets,
                call_offset + batch_number - 1,
                max_tokens=LOCAL_NOTE_MAX_TOKENS,
                success_predicate=lambda parsed, batch_chunks=chunk_batch: has_complete_chunk_note_result(parsed, batch_chunks),
                response_schema=hierarchical_abstractive_schema_for_chunks(chunk_batch),
            )
            for run in batch_runs:
                run["batch_number"] = batch_number
                run["chunk_ids"] = [chunk["chunk_id"] for chunk in chunk_batch]
            return batch_runs

        for batch_runs in parallel_map_ordered(chunk_batches, run_batch, max_workers=model_stage_max_workers(targets)):
            runs.extend(batch_runs)
        return runs


def segment_utterances_texttiling(
    utterances: list[Utterance],
    window_utterances: int = WINDOW_UTTERANCES,
    stride_utterances: int = STRIDE_UTTERANCES,
    max_segments: int = 10,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not utterances:
        return [], []
    if len(utterances) <= CHUNK_UTTERANCES:
        return [{"start": 0, "end": len(utterances), "utterances": utterances}], []

    block_utterances = max(4, window_utterances // 2)
    candidate_gaps = list(range(stride_utterances, len(utterances), stride_utterances)) or [len(utterances) // 2]
    trace = []
    gap_scores = []
    for gap in candidate_gaps:
        left_start = max(0, gap - block_utterances)
        right_end = min(len(utterances), gap + block_utterances)
        left_counter = Counter(token for item in utterances[left_start:gap] for token in tokenize_for_similarity(item.text))
        right_counter = Counter(token for item in utterances[gap:right_end] for token in tokenize_for_similarity(item.text))
        similarity = cosine_similarity(left_counter, right_counter)
        gap_scores.append(similarity)
        trace.append(
            {
                "boundary_after": utterances[gap - 1].index,
                "gap_position": gap,
                "left_utterance_ids": [item.index for item in utterances[left_start:gap]],
                "right_utterance_ids": [item.index for item in utterances[gap:right_end]],
                "cosine_similarity": round(similarity, 4),
                "selected": False,
            }
        )

    smoothed_scores = smooth_texttiling_scores(gap_scores)
    depth_scores = texttiling_depth_scores(smoothed_scores)
    threshold = texttiling_depth_threshold(depth_scores)
    for index, item in enumerate(trace):
        item["smoothed_similarity"] = round(smoothed_scores[index], 4)
        item["depth_score"] = round(depth_scores[index], 4)
        item["threshold"] = round(threshold, 4)

    selected = []
    minimum_boundary_gap = max(stride_utterances, window_utterances)
    for item in sorted(trace, key=lambda value: value["depth_score"], reverse=True):
        if item["depth_score"] < threshold:
            continue
        if any(abs(item["gap_position"] - existing["gap_position"]) < minimum_boundary_gap for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= max_segments - 1:
            break
    if not selected and len(utterances) > window_utterances:
        selected = [max(trace, key=lambda value: value["depth_score"])]

    boundaries = sorted(item["gap_position"] for item in selected)
    for item in trace:
        if item["gap_position"] in boundaries:
            item["selected"] = True

    segments = []
    start = 0
    for boundary in boundaries + [len(utterances)]:
        if boundary <= start:
            continue
        segments.append({"start": start, "end": boundary, "utterances": utterances[start:boundary]})
        start = boundary
    return segments, trace


def smooth_texttiling_scores(scores: list[float], radius: int = 1) -> list[float]:
    if len(scores) <= 2 or radius <= 0:
        return list(scores)
    smoothed = []
    for index in range(len(scores)):
        start = max(0, index - radius)
        end = min(len(scores), index + radius + 1)
        smoothed.append(sum(scores[start:end]) / (end - start))
    return smoothed


def texttiling_depth_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    if len(scores) <= 2:
        return [max(0.0, 1.0 - score) for score in scores]
    depth_scores = []
    for index, score in enumerate(scores):
        left_peak = score
        for left_index in range(index - 1, -1, -1):
            if scores[left_index] >= left_peak:
                left_peak = scores[left_index]
            else:
                break

        right_peak = score
        for right_index in range(index + 1, len(scores)):
            if scores[right_index] >= right_peak:
                right_peak = scores[right_index]
            else:
                break

        depth_scores.append(max(0.0, left_peak + right_peak - (2 * score)))
    return depth_scores


def texttiling_depth_threshold(depth_scores: list[float]) -> float:
    if not depth_scores:
        return 1.0
    if len(depth_scores) == 1:
        return depth_scores[0]
    return statistics.mean(depth_scores) + (statistics.pstdev(depth_scores) * 0.5)


def chunk_segment(segment_utterances: list[Utterance]) -> list[dict[str, Any]]:
    chunks = []
    for offset in range(0, len(segment_utterances), CHUNK_UTTERANCES):
        chunk_utterances = segment_utterances[offset : offset + CHUNK_UTTERANCES]
        chunks.append(
            {
                "chunk_id": f"chunk-{chunk_utterances[0].index}-{chunk_utterances[-1].index}",
                "utterances": chunk_utterances,
                "utterance_ids": [item.index for item in chunk_utterances],
                "start_time": chunk_utterances[0].start_time,
                "end_time": chunk_utterances[-1].end_time,
                "estimated_tokens": estimate_tokens(" ".join(item.text for item in chunk_utterances)),
            }
        )
    return chunks


def build_hierarchical_title_prompt(input_name: str, chapter_number: int, segment_utterances: list[Utterance]) -> str:
    template = PromptLoader.get_prompt("hierarchical_title")
    return (
        template.replace("{input_name}", input_name)
        .replace("{chapter_number}", str(chapter_number))
        .replace("{segment_utterances}", format_utterances(segment_utterances, max_chars=18000))
    )


def build_hierarchical_abstractive_prompt(input_name: str, chapter_number: int, chunks: list[dict[str, Any]]) -> str:
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
    template = PromptLoader.get_prompt("hierarchical_abstractive")
    return (
        template.replace("{input_name}", input_name)
        .replace("{chapter_number}", str(chapter_number))
        .replace("{required_chunk_ids}", json.dumps(required_chunk_ids, ensure_ascii=False, indent=2))
        .replace("{prompt_chunks}", json.dumps(prompt_chunks, ensure_ascii=False, indent=2))
        .replace("{example_chunk_id}", example_chunk_id)
    )


def hierarchical_abstractive_batches(chunks: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [[chunk] for chunk in chunks]


def hierarchical_abstractive_schema_for_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
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


def parse_title_result(runs: list[dict[str, Any]], segment_utterances: list[Utterance]) -> dict[str, str]:
    fallback = fallback_title_result(segment_utterances)
    for run in runs:
        if run.get("error"):
            continue
        parsed = run.get("parsed")
        if not isinstance(parsed, dict):
            continue
        title = clean_text(parsed.get("title"))
        summary = clean_text(parsed.get("one_line_summary"))
        if title or summary:
            return {"title": title or fallback["title"], "one_line_summary": summary or fallback["one_line_summary"]}
    return fallback


def parse_chunk_notes(runs: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
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


def fallback_title_result(segment_utterances: list[Utterance]) -> dict[str, str]:
    if not segment_utterances:
        return {
            "title": "Chapter chưa có nội dung",
            "one_line_summary": "Chapter này không có utterance transcript để tóm tắt.",
        }
    title_source = first_non_empty_utterance_text(segment_utterances)
    start_id = segment_utterances[0].index
    end_id = segment_utterances[-1].index
    title = truncate_words(title_source, 8) or f"Chủ đề U{start_id}-U{end_id}"
    summary_source = summarize_utterance_texts(segment_utterances, max_words=34)
    summary = f"Chapter ghi nhận nội dung: {as_sentence(summary_source)}" if summary_source else f"Chapter bao gồm các utterance U{start_id}-U{end_id}."
    return {"title": title, "one_line_summary": summary}


def fallback_chunk_summary(chunk: dict[str, Any] | None) -> str:
    if not chunk:
        return "Đoạn này không có nội dung transcript rõ ràng để tóm tắt."
    utterances = chunk.get("utterances", []) or []
    summary_source = summarize_utterance_texts(utterances, max_words=36)
    if summary_source:
        return f"Đoạn này ghi nhận: {as_sentence(summary_source)}"
    chunk_id = clean_text(chunk.get("chunk_id"))
    return f"Đoạn {chunk_id or 'này'} không có nội dung transcript rõ ràng để tóm tắt."


def first_non_empty_utterance_text(utterances: list[Utterance]) -> str:
    for utterance in utterances:
        text = clean_text(utterance.text)
        if text:
            return text
    return ""


def summarize_utterance_texts(utterances: list[Utterance], max_words: int) -> str:
    text = " ".join(clean_text(utterance.text) for utterance in utterances if clean_text(utterance.text))
    return truncate_words(text, max_words)


def truncate_words(text: str, max_words: int) -> str:
    words = clean_text(text).split()
    if not words:
        return ""
    truncated = " ".join(words[:max_words])
    if len(words) > max_words:
        return f"{truncated}..."
    return truncated


def as_sentence(text: str) -> str:
    stripped = clean_text(text)
    if not stripped:
        return ""
    if stripped.endswith(("...", ".", "!", "?", "。", "！", "？")):
        return stripped
    return f"{stripped}."


def iter_chunk_note_items(parsed: dict[str, Any] | list[Any], notes_by_chunk: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    default_chunk_id = next(iter(notes_by_chunk)) if len(notes_by_chunk) == 1 else ""
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                items.append(item)
            elif isinstance(item, list):
                items.extend(iter_chunk_note_items(item, notes_by_chunk))
            elif isinstance(item, str) and default_chunk_id:
                items.append({"chunk_id": default_chunk_id, "summary": item})
        return items

    for key in ("notes", "chunks", "chunk_notes", "summaries", "items"):
        value = parsed.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    items.append(item)
                elif isinstance(item, list):
                    items.extend(iter_chunk_note_items(item, notes_by_chunk))
                elif isinstance(item, str) and default_chunk_id:
                    items.append({"chunk_id": default_chunk_id, "summary": item})
    for key, value in parsed.items():
        if key in notes_by_chunk:
            if isinstance(value, str):
                items.append({"chunk_id": key, "summary": value})
            elif isinstance(value, dict):
                merged = dict(value)
                merged.setdefault("chunk_id", key)
                items.append(merged)
    return items


def attach_unknown_notes_by_order(
    notes_by_chunk: dict[str, list[dict[str, Any]]],
    chunks: list[dict[str, Any]],
    unknown_chunk_notes: list[dict[str, Any]],
) -> None:
    missing_chunk_ids = [chunk["chunk_id"] for chunk in chunks if not notes_by_chunk[chunk["chunk_id"]]]
    if unknown_chunk_notes and len(unknown_chunk_notes) == len(missing_chunk_ids):
        for chunk_id, note_record in zip(missing_chunk_ids, unknown_chunk_notes):
            notes_by_chunk[chunk_id].append(note_record)


def fill_missing_chunk_notes(notes_by_chunk: dict[str, list[dict[str, Any]]], chunks: list[dict[str, Any]]) -> None:
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        if notes_by_chunk.get(chunk_id):
            continue
        notes_by_chunk[chunk_id].append(
            {
                "summary": fallback_chunk_summary(chunk),
                "contains_key_point": False,
                "contains_action_item": False,
                "generated_by": "local-fallback",
            }
        )


def render_chunks(chunks: list[dict[str, Any]], notes_by_chunk: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rendered_chunks = []
    for chunk in chunks:
        rendered_chunks.append(
            {
                "chunk_id": chunk["chunk_id"],
                "utterance_ids": chunk["utterance_ids"],
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "estimated_tokens": chunk["estimated_tokens"],
                "utterances": [utterance_to_dict(item) for item in chunk["utterances"]],
                "notes": notes_by_chunk.get(chunk["chunk_id"], []),
            }
        )
    return rendered_chunks


def deduplicate_note_records(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduplicated = []
    for note in notes:
        summary = clean_text(note.get("summary"))
        if not summary or summary in seen:
            continue
        seen.add(summary)
        deduplicated.append(note)
    return deduplicated


def is_valid_title_result(parsed: Any) -> bool:
    return isinstance(parsed, dict)


def has_complete_chunk_note_result(parsed: Any, chunks: list[dict[str, Any]]) -> bool:
    return isinstance(parsed, (dict, list))


def build_timespan(utterances: list[Utterance]) -> str:
    if not utterances:
        return ""
    start = utterances[0].start_time or "?"
    end = utterances[-1].end_time or "?"
    return f"{start}-{end}"
