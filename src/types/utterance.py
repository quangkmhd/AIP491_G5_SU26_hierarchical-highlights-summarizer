"""Utterance -- the smallest unit of a meeting transcript.

A single spoken statement by one speaker. Immutable once created because
utterances are raw input data and form the ordering base for downstream
segmentation and summarization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import Field

from ._base import BaseSchema


class Utterance(BaseSchema):
    """A single spoken statement by one speaker in a meeting transcript.

    Immutable once created -- utterances are raw input data.
    """

    model_config = BaseSchema.model_config | {"frozen": True}

    speaker: str = Field(
        ...,
        min_length=1,
        description="Speaker label (e.g. 'A', 'B', or a real name).",
    )
    text: str = Field(
        ...,
        min_length=1,
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
