from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .utterance import Utterance


class Chunk(BaseModel):
    """Khối câu thoại được tóm tắt bằng ViT5."""

    utterances: list[Utterance] = Field(default_factory=list)
    rolling_summary: str = Field(default="")
    chunk_id: UUID = Field(default_factory=uuid4)


class SegmentResult(BaseModel):
    """Phân đoạn chủ đề chứa tiêu đề chương từ BARTpho và danh sách các khối Chunk."""

    title: str = Field(default="")
    chunks: list[Chunk] = Field(default_factory=list)
    segment_id: UUID = Field(default_factory=uuid4)
    utterances_start: int = Field(default=0, ge=0)
    utterances_end: int = Field(default=0, ge=0)
