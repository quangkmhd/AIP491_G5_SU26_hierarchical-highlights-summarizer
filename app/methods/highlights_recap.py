from typing import Any

from app.services.completion_client import (
    JsonCompletionRunner,
    complete_json_with_target_fallback,
    normalized_model_runs,
)
from app.services.model_targets import ModelTarget, model_stage_max_workers
from app.services.llm_output_schemas import is_valid_highlights_rewrite_output
from app.services.parallel import parallel_map_ordered
from app.services.prompt_loader import PromptLoader
from app.services.text_utils import clean_text, chunked_sequence, estimate_tokens
from app.services.transcript_parser import (
    Utterance,
    abstract_context_for_utterance,
    context_for_utterance,
    utterance_by_id,
    utterance_to_dict,
)


HIGHLIGHTS_CONTEXT_UTTERANCES = 10
ABSTRACTIVE_CONTEXT_TOKENS = 512
EXTRACTIVE_MAX_TOKENS = 128
ABSTRACTIVE_MAX_TOKENS = 384


class HighlightsRecapMethod:
    name = "highlights"

    def summarize(
        self,
        utterances: list[Utterance],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        input_name: str,
    ) -> dict[str, Any]:
        if not utterances:
            return {"method": self.name, "notes": [], "tasks": [], "selected_candidates": [], "windows": [], "model_runs": []}

        windows = build_highlights_extractive_windows(utterances)
        extract_runs = self._run_extractive_stage(utterances, runner, targets, input_name)
        allowed_center_ids = {window["center_utterance"]["id"] for window in windows}
        key_points, action_items = parse_extractive_candidates(extract_runs, allowed_center_ids)
        key_points = key_points[:12]
        action_items = action_items[:12]

        selected_contexts = build_candidate_contexts(utterances, key_points + action_items)
        rewrite_runs = self._run_abstractive_stage(selected_contexts, len(extract_runs), runner, targets, input_name, utterances)
        notes = merge_rewritten_items(utterances, rewrite_runs, key_points, "notes")
        tasks = merge_rewritten_items(utterances, rewrite_runs, action_items, "tasks")
        return {
            "method": self.name,
            "paper_mapping": {
                "design_rationale": "DR1 - concise outcomes for planning and coordination",
                "extractive_window": "highlights_extractive substitute over about 10 utterances / 106-token context",
                "abstractive_context": "highlights_abstractive substitute with 512-token surrounding context and third-person rewriting",
                "ux_shape": "flat AI Notes and AI Tasks lists with source context",
            },
            "notes": notes,
            "tasks": tasks,
            "selected_candidates": selected_contexts,
            "windows": build_highlights_windows_trace(utterances),
            "model_runs": normalized_model_runs("highlights_extractive", extract_runs)
            + normalized_model_runs("highlights_abstractive", rewrite_runs),
        }

    def _run_extractive_stage(
        self,
        utterances: list[Utterance],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        input_name: str,
    ) -> list[dict[str, Any]]:
        windows = list(enumerate(build_highlights_extractive_windows(utterances), start=1))

        def run_window(window_item: tuple[int, dict[str, Any]]) -> list[dict[str, Any]]:
            window_number, window = window_item
            center_utterance_id = window["center_utterance"]["id"]
            prompt = build_single_extractive_prompt(input_name, window)
            window_runs = complete_json_with_target_fallback(
                runner,
                "highlights_extractive",
                prompt,
                targets,
                start_offset=window_number - 1,
                max_tokens=EXTRACTIVE_MAX_TOKENS,
            )
            for run in window_runs:
                run["window_number"] = window_number
                run["center_utterance_ids"] = [center_utterance_id]
                run["context_utterance_ids"] = window["utterance_ids"]
            return window_runs

        runs: list[dict[str, Any]] = []
        for window_runs in parallel_map_ordered(windows, run_window, max_workers=model_stage_max_workers(targets)):
            runs.extend(window_runs)
        return runs

    def _run_abstractive_stage(
        self,
        selected_contexts: list[dict[str, Any]],
        offset: int,
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        input_name: str,
        utterances: list[Utterance],
    ) -> list[dict[str, Any]]:
        batch_size = 1
        batches = list(enumerate(chunked_sequence(selected_contexts, batch_size), start=1))

        def run_batch(batch: tuple[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
            batch_number, rewrite_batch = batch
            prompt = build_highlights_abstractive_prompt(input_name, rewrite_batch)
            batch_runs = complete_json_with_target_fallback(
                runner,
                "highlights_abstractive",
                prompt,
                targets,
                start_offset=offset + batch_number - 1,
                max_tokens=ABSTRACTIVE_MAX_TOKENS,
                success_predicate=lambda parsed, contexts=rewrite_batch: has_complete_rewrite_result(parsed, contexts),
                response_schema=highlights_abstractive_schema_for_candidates(rewrite_batch),
            )
            for run in batch_runs:
                run["batch_number"] = batch_number
                run["candidate_utterance_ids"] = [item["utterance_id"] for item in rewrite_batch]
            return batch_runs

        runs: list[dict[str, Any]] = []
        for batch_runs in parallel_map_ordered(batches, run_batch, max_workers=model_stage_max_workers(targets)):
            runs.extend(batch_runs)
        return runs


def highlights_abstractive_schema_for_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    note_ids = [int(item["utterance_id"]) for item in candidates if item.get("type") == "key_point"]
    task_ids = [int(item["utterance_id"]) for item in candidates if item.get("type") == "action_item"]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "notes": array_schema_for_highlight_notes(note_ids),
            "tasks": array_schema_for_highlight_tasks(task_ids),
        },
        "required": ["notes", "tasks"],
    }


def array_schema_for_highlight_notes(utterance_ids: list[int]) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "minItems": len(utterance_ids),
        "maxItems": len(utterance_ids),
    }
    if utterance_ids:
        schema["items"] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "utterance_id": {"type": "integer", "enum": utterance_ids},
                "summary": {"type": "string", "minLength": 1},
            },
            "required": ["utterance_id", "summary"],
        }
    else:
        schema["items"] = {"type": "object"}
    return schema


def array_schema_for_highlight_tasks(utterance_ids: list[int]) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "minItems": len(utterance_ids),
        "maxItems": len(utterance_ids),
    }
    if utterance_ids:
        schema["items"] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "utterance_id": {"type": "integer", "enum": utterance_ids},
                "summary": {"type": "string", "minLength": 1},
                "assignee": {"type": "string"},
                "due": {"type": "string"},
            },
            "required": ["utterance_id", "summary", "assignee", "due"],
        }
    else:
        schema["items"] = {"type": "object"}
    return schema


def build_highlights_extractive_windows(utterances: list[Utterance]) -> list[dict[str, Any]]:
    windows = []
    for utterance in utterances:
        index = utterance.index - 1
        start = max(0, index - (HIGHLIGHTS_CONTEXT_UTTERANCES // 2))
        end = min(len(utterances), start + HIGHLIGHTS_CONTEXT_UTTERANCES)
        start = max(0, end - HIGHLIGHTS_CONTEXT_UTTERANCES)
        window_utterances = utterances[start:end]
        windows.append(
            {
                "center_utterance": utterance_to_dict(utterance),
                "context_utterances": [utterance_to_dict(item) for item in window_utterances],
                "utterance_ids": [item.index for item in window_utterances],
                "estimated_tokens": estimate_tokens(" ".join(item.text for item in window_utterances)),
            }
        )
    return windows


def build_highlights_windows_trace(utterances: list[Utterance], max_windows: int = 40) -> list[dict[str, Any]]:
    return [
        {
            "center_utterance_id": window["center_utterance"]["id"],
            "utterance_ids": window["utterance_ids"],
            "estimated_tokens": window["estimated_tokens"],
        }
        for window in build_highlights_extractive_windows(utterances)[:max_windows]
    ]


def build_single_extractive_prompt(input_name: str, window: dict[str, Any]) -> str:
    template = PromptLoader.get_prompt("highlights_extractive")
    return template.replace("{input_name}", input_name).replace(
        "{extractive_batch_markdown}", format_single_extractive_markdown(window)
    )


def build_highlights_abstractive_prompt(input_name: str, candidates: list[dict[str, Any]]) -> str:
    template = PromptLoader.get_prompt("highlights_abstractive")
    allowed_note_ids = [item["utterance_id"] for item in candidates if item.get("type") == "key_point"]
    allowed_task_ids = [item["utterance_id"] for item in candidates if item.get("type") == "action_item"]
    return (
        template.replace("{input_name}", input_name)
        .replace("{allowed_note_utterance_ids}", format_id_list(allowed_note_ids))
        .replace("{allowed_task_utterance_ids}", format_id_list(allowed_task_ids))
        .replace("{candidates_markdown}", format_candidates_markdown(candidates))
    )


def format_single_extractive_markdown(window: dict[str, Any]) -> str:
    center_utterance_id = window.get("center_utterance", {}).get("id", "")
    lines = [
        "## Candidate center utterance IDs",
        f"Candidate center utterance IDs to classify: {center_utterance_id}",
        "",
        "## Shared transcript context in chronological order",
        "Use these lines to understand the meeting flow. Only classify the candidate center ID listed above.",
    ]
    for item in window.get("context_utterances", []) or []:
        lines.append(format_utterance_markdown(item))
    lines.extend(
        [
            "",
            "## Window metadata",
            f"Context utterance IDs included: {format_id_list(window.get('utterance_ids', []))}",
            f"Estimated context tokens: {window.get('estimated_tokens', '')}",
        ]
    )
    return "\n".join(lines)


def format_candidates_markdown(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "No selected extractive candidates."
    sections: list[str] = []
    for position, candidate in enumerate(candidates, start=1):
        context_lines = [format_utterance_markdown(item) for item in candidate.get("context_512_token_budget", []) or []]
        sections.append(
            "\n".join(
                [
                    f"## Candidate {position}",
                    f"Type: {candidate.get('type', '')}",
                    f"Output utterance_id: {candidate.get('utterance_id', '')}",
                    f"Source utterance: {format_utterance_inline(candidate.get('source_utterance', {}))}",
                    "",
                    "Conversation context within 512-token budget, chronological and includes the source utterance:",
                    *(context_lines or ["- No surrounding context available."]),
                ]
            )
        )
    return "\n\n".join(sections)


def format_id_list(ids: list[int] | tuple[int, ...] | set[int]) -> str:
    normalized = [str(item) for item in ids]
    return ", ".join(normalized) if normalized else "none"


def format_utterance_markdown(item: dict[str, Any]) -> str:
    return f"- {format_utterance_inline(item)}"


def format_utterance_inline(item: dict[str, Any]) -> str:
    utterance_id = item.get("id", "")
    speaker = clean_text(str(item.get("speaker", ""))) or "Unknown"
    start_time = str(item.get("start_time", "") or "")
    end_time = str(item.get("end_time", "") or "")
    timespan = f"{start_time}-{end_time}" if start_time or end_time else "no-time"
    text = clean_text(str(item.get("text", "")))
    return f"U{utterance_id} | {speaker} | {timespan} | {text}"


def parse_extractive_candidates(
    runs: list[dict[str, Any]],
    allowed_utterance_ids: set[int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key_points: dict[int, dict[str, Any]] = {}
    action_items: dict[int, dict[str, Any]] = {}

    for run in runs:
        parsed = run.get("parsed")
        if not isinstance(parsed, dict):
            continue

        if "utterance_id" in parsed and ("is_key_point" in parsed or "is_action_item" in parsed):
            try:
                utterance_id = int(parsed.get("utterance_id"))
            except (TypeError, ValueError):
                continue
            if allowed_utterance_ids is not None and utterance_id not in allowed_utterance_ids:
                continue
            if truthy_flag(parsed.get("is_key_point")) and utterance_id not in key_points:
                key_points[utterance_id] = {"utterance_id": utterance_id, "type": "key_point"}
            if truthy_flag(parsed.get("is_action_item")) and utterance_id not in action_items:
                action_items[utterance_id] = {"utterance_id": utterance_id, "type": "action_item"}
            continue

        for item in parsed.get("key_points", []) or []:
            add_legacy_candidate(item, key_points, "key_point", allowed_utterance_ids)
        for item in parsed.get("action_items", []) or []:
            add_legacy_candidate(item, action_items, "action_item", allowed_utterance_ids)

    return (
        [key_points[key] for key in sorted(key_points)],
        [action_items[key] for key in sorted(action_items)],
    )


def add_legacy_candidate(
    item: Any,
    candidates: dict[int, dict[str, Any]],
    item_type: str,
    allowed_utterance_ids: set[int] | None = None,
) -> None:
    if not isinstance(item, dict):
        return
    try:
        utterance_id = int(item.get("utterance_id"))
    except (TypeError, ValueError):
        return
    if allowed_utterance_ids is not None and utterance_id not in allowed_utterance_ids:
        return
    if utterance_id not in candidates:
        candidates[utterance_id] = {"utterance_id": utterance_id, "type": item_type}


def truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1"}
    return False


def build_candidate_contexts(utterances: list[Utterance], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = utterance_by_id(utterances)
    contexts = []
    for candidate in candidates:
        utterance_id = candidate["utterance_id"]
        source = by_id.get(utterance_id)
        if not source:
            continue
        contexts.append(
            {
                "type": candidate["type"],
                "utterance_id": utterance_id,
                "source_utterance": utterance_to_dict(source),
                "context_512_token_budget": abstract_context_for_utterance(
                    utterances,
                    utterance_id,
                    ABSTRACTIVE_CONTEXT_TOKENS,
                ),
            }
        )
    return contexts


def merge_rewritten_items(
    utterances: list[Utterance],
    runs: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    output_key: str,
) -> list[dict[str, Any]]:
    by_id = utterance_by_id(utterances)
    candidate_by_id = {candidate["utterance_id"]: candidate for candidate in candidates}
    merged: dict[int, dict[str, Any]] = {}
    for run in runs:
        if run.get("error"):
            continue
        parsed = run.get("parsed")
        if not isinstance(parsed, dict):
            continue
        for item in parsed.get(output_key, []) or []:
            try:
                utterance_id = int(item.get("utterance_id"))
            except (TypeError, ValueError):
                continue
            summary = clean_text(item.get("summary"))
            if not summary or utterance_id not in by_id:
                continue
            if utterance_id not in candidate_by_id:
                continue
            if utterance_id in merged:
                continue
            candidate = candidate_by_id.get(utterance_id, {})
            rewritten_by = run.get("target", "")
            merged[utterance_id] = {
                "summary": summary,
                "source_utterance_id": utterance_id,
                "source_text": by_id[utterance_id].text,
                "assignee": clean_text(item.get("assignee")) or clean_text(candidate.get("assignee")),
                "due": clean_text(item.get("due")) or clean_text(candidate.get("due")),
                "context": context_for_utterance(utterances, utterance_id),
                "rewritten_by": rewritten_by,
                "rewrite_warning": "",
            }
    return [merged[key] for key in sorted(merged)]


def has_complete_rewrite_result(parsed: Any, candidate_contexts: list[dict[str, Any]]) -> bool:
    return is_valid_highlights_rewrite_output(parsed, candidate_contexts)
