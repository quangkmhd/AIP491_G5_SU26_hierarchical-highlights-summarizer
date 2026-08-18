from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import Field

from ._base import BaseSchema
# Highlight family removed in model-001+ (DR1 dropped from scope).
from .segment import SegmentResult


class MeetingStatus(str, Enum):
    """Lifecycle state of a meeting processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HierarchicalRecap(BaseSchema):
    """The complete hierarchical meeting recap output.

    Contains all topic-segmented chapters with their titles and rolling
    summaries. Highlights (notes and tasks) were removed in model-001+ because
    the product surface is hierarchical-only (DR1 dropped from scope).
    """

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
