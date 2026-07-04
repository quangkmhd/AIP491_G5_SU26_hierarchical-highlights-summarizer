"""HierarchicalRecap -- the final structured output of the meeting recap system."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import Field

from ._base import BaseSchema
from .highlight import Highlight
from .segment import SegmentResult


class MeetingStatus(str, Enum):
    """Lifecycle state of a meeting processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HierarchicalRecap(BaseSchema):
    """The complete hierarchical meeting recap output.

    Contains all topic-segmented chapters with their titles, rolling summaries,
    and all extracted/user-created highlights (notes and tasks).
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
    highlights_notes: list[Highlight] = Field(
        default_factory=list,
        description="Global key-point highlights (UI calls these 'AI notes').",
    )
    highlights_tasks: list[Highlight] = Field(
        default_factory=list,
        description="Global action-item highlights (UI calls these 'AI tasks').",
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

    @property
    def all_highlights(self) -> list[Highlight]:
        return [*self.highlights_notes, *self.highlights_tasks]

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    @property
    def total_chunks(self) -> int:
        return sum(s.chunk_count for s in self.segments)
