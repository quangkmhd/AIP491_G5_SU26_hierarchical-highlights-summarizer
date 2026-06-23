"""Dataclasses and Pydantic models shared across the lexnorm package.

These types are intentionally kept decoupled so the lexnorm package has no
cross-tool-09 import dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Utterance:
    index: int
    speaker: str
    start_time: str
    end_time: str
    text: str


@dataclass(frozen=True)
class CorrectionResult:
    utterance_id: int
    raw_text: str
    corrected_text: str
    accepted: bool
    rejection_reason: str
    model_run: dict


class ErrorWord(BaseModel):
    raw: str
    target: str


class CorrectionResponse(BaseModel):
    error_words: list[ErrorWord] = Field(default_factory=list)
    llm_corrected: str
