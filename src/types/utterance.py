from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Utterance(BaseModel):
    """A single spoken statement by one speaker in a meeting transcript.

    Immutable once created -- utterances are raw input data.
    """

    model_config = ConfigDict(frozen=True)

    speaker: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Speaker label (e.g. 'no.0', 'no.1', 'no.2').",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Verbatim text of the spoken utterance.",
    )
    index: int = Field(
        ...,
        ge=0,
        description="0-based position of the utterance in the transcript.",
    )
    utterance_id: UUID = Field(
        default_factory=uuid4,
        description="Stable unique identifier for this utterance.",
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Optional wall-clock timestamp for the utterance.",
    )
