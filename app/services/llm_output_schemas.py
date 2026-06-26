from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.services.text_utils import clean_text


class HighlightNoteOutput(BaseModel):
    utterance_id: int
    summary: str = Field(..., min_length=1)


class HighlightTaskOutput(BaseModel):
    utterance_id: int
    summary: str = Field(..., min_length=1)
    assignee: str = ""
    due: str = ""


class HighlightsExtractiveOutput(BaseModel):
    utterance_id: int
    is_key_point: bool
    is_action_item: bool


class HighlightsRewriteOutput(BaseModel):
    notes: list[HighlightNoteOutput] = Field(default_factory=list)
    tasks: list[HighlightTaskOutput] = Field(default_factory=list)


class HierarchicalTitleOutput(BaseModel):
    title: str = Field(..., min_length=1)
    one_line_summary: str = ""


class ChunkNoteOutput(BaseModel):
    chunk_id: str = ""
    summary: str = Field(..., min_length=1)
    contains_key_point: bool = False
    contains_action_item: bool = False


class HierarchicalAbstractiveOutput(BaseModel):
    notes: list[ChunkNoteOutput] = Field(default_factory=list)


class SsDstStateOutput(BaseModel):
    current_topic: str = ""
    entities: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    open_actions: list[str] = Field(default_factory=list)
    resolved_references: list[dict[str, str]] = Field(default_factory=list)


def response_schema_for_task(task_name: str) -> dict[str, Any] | None:
    if task_name == "highlights_extractive":
        return HighlightsExtractiveOutput.model_json_schema()
    if task_name == "highlights_abstractive":
        return HighlightsRewriteOutput.model_json_schema()
    if task_name == "hierarchical_title":
        return HierarchicalTitleOutput.model_json_schema()
    if task_name == "hierarchical_abstractive":
        return HierarchicalAbstractiveOutput.model_json_schema()
    if task_name == "ssdst_abstractive":
        return HierarchicalAbstractiveOutput.model_json_schema()
    if task_name == "ssdst_state_update":
        return SsDstStateOutput.model_json_schema()
    return None


def is_valid_highlights_rewrite_output(parsed: Any, candidate_contexts: list[dict[str, Any]]) -> bool:
    try:
        model = HighlightsRewriteOutput.model_validate(parsed)
    except ValidationError:
        return False

    expected_notes = {item["utterance_id"] for item in candidate_contexts if item.get("type") == "key_point"}
    expected_tasks = {item["utterance_id"] for item in candidate_contexts if item.get("type") == "action_item"}
    found_notes = {item.utterance_id for item in model.notes if clean_text(item.summary)}
    found_tasks = {item.utterance_id for item in model.tasks if clean_text(item.summary)}
    return found_notes == expected_notes and found_tasks == expected_tasks


def is_valid_chunk_note_item(note: Any) -> bool:
    try:
        model = ChunkNoteOutput.model_validate(note)
    except ValidationError:
        return False
    return bool(clean_text(model.summary))
