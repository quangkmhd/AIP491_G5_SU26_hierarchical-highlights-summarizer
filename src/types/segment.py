"""Segment and Chunk types -- topic boundaries and sub-block structures."""

from __future__ import annotations

from typing import ClassVar, Optional
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from ._base import BaseSchema
from .utterance import Utterance


class Chunk(BaseSchema):
    """A sub-block of up to 8 utterances within a segment.

    Chunks are the unit sent to abstractive summarizers (deBERTa/BART)
    which have a strict 512-token input limit.
    """

    chunk_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this chunk.",
    )
    utterances: list[Utterance] = Field(
        ...,
        min_length=1,
        description="Utterances inside this chunk (typically <= MAX_CHUNK_SIZE).",
    )
    rolling_summary: Optional[str] = Field(
        default=None,
        description="3rd-person abstractive summary of the chunk.",
    )

    # ClassVar so the limit is a true constant, not a per-instance field.
    MAX_CHUNK_SIZE: ClassVar[int] = 8

    @model_validator(mode="after")
    def _check_chunk_size(self) -> "Chunk":
        if len(self.utterances) > self.MAX_CHUNK_SIZE:
            raise ValueError(
                f"Chunk has {len(self.utterances)} utterances, "
                f"exceeds MAX_CHUNK_SIZE={self.MAX_CHUNK_SIZE}."
            )
        return self


class SegmentResult(BaseSchema):
    """A detected topic segment (chapter) with its title, chunks, and metadata.

    Represents the output of the TextTiling algorithm -- a contiguous range
    of utterances that form a coherent topic.
    """

    segment_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this segment.",
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Auto-generated chapter title (e.g. from deBERTa).",
    )
    chunks: list[Chunk] = Field(
        default_factory=list,
        description="Ordered list of 1..N chunks (each <= 8 utterances).",
    )
    utterances_start: int = Field(
        ...,
        ge=0,
        description="Index of the first utterance in the segment.",
    )
    utterances_end: int = Field(
        ...,
        ge=0,
        description="Index of the last utterance in the segment (inclusive).",
    )
    user_title_override: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Human-edited chapter title (takes precedence over `title`).",
    )

    @property
    def display_title(self) -> str:
        """Return the user-overridden title if present, otherwise the auto title."""
        if self.user_title_override is not None:
            return self.user_title_override
        return self.title

    @property
    def utterance_count(self) -> int:
        if self.utterances_end < self.utterances_start:
            return 0
        return self.utterances_end - self.utterances_start + 1

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
