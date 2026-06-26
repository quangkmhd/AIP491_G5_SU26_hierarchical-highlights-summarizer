from typing import Any, Literal

from pydantic import BaseModel, Field


SummaryMethod = Literal["highlights", "hierarchical", "ssdst", "both"]


class SummaryRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    method: SummaryMethod = "both"
    input_name: str = Field(default="frontend-input.md", min_length=1, max_length=160)


class SummaryResponse(BaseModel):
    input_name: str
    method: SummaryMethod
    utterance_count: int
    model_targets: list[dict[str, str]]
    langfuse_enabled: bool = False
    langfuse_trace_id: str = ""
    langfuse_observation_id: str = ""
    results: dict[str, Any]
