from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .utterance import Utterance


class Chunk(BaseModel):
    """Fixed-size chunk of utterances summarized by ViT5."""

    MAX_CHUNK_SIZE: ClassVar[int] = 8

    utterances: list[Utterance] = Field(default_factory=list)
    rolling_summary: str = Field(default="")
    chunk_id: UUID = Field(default_factory=uuid4)

    def get_utterance_count(self) -> int:
        return len(self.utterances)


class SegmentResult(BaseModel):
    """Topic segment containing topic title from BARTpho and member chunks."""

    title: str = Field(default="")
    chunks: list[Chunk] = Field(default_factory=list)
    segment_id: UUID = Field(default_factory=uuid4)
    utterances_start: int = Field(default=0, ge=0)
    utterances_end: int = Field(default=0, ge=0)

    def get_chunk_count(self) -> int:
        return len(self.chunks)
