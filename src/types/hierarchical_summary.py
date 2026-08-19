from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .segment import SegmentResult


class HierarchicalSummary(BaseModel):
    """Kết quả tóm tắt phân cấp cuộc họp hoàn chỉnh gồm các chương và khối tóm tắt."""

    meeting_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this meeting.",
    )
    meeting_title: Optional[str] = Field(
        default=None,
        description="Display title for the meeting (if known).",
    )
    segments: list[SegmentResult] = Field(
        default_factory=list,
        description="Topic-segmented chapters in chronological order.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp the recap was generated.",
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total processing time in milliseconds.",
    )

    def get_segment_count(self) -> int:
        return len(self.segments)

    def get_total_chunks(self) -> int:
        return sum(s.get_chunk_count() for s in self.segments)
