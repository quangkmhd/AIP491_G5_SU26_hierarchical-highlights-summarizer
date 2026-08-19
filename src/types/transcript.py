from __future__ import annotations

from datetime import datetime, timezone
from itertools import pairwise
from typing import ClassVar, Iterator, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .utterance import Utterance


class DialogueTranscript(BaseModel):
    """Bản ghi cuộc họp gồm danh sách thứ tự các câu thoại Utterance."""

    utterances: list[Utterance] = Field(
        ...,
        min_length=1,
        description="Ordered list of utterances that make up the meeting.",
    )
    meeting_title: Optional[str] = Field(
        default=None,
        description="Optional human-readable meeting title.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary string-keyed metadata.",
    )
    transcript_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this transcript submission.",
    )
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp the transcript was submitted.",
    )

    MAX_UTTERANCES: ClassVar[int] = 5000

    def get_utterance_count(self) -> int:
        return len(self.utterances)

    def get_utterance_pairs(self) -> Iterator[tuple[Utterance, Utterance]]:
        """Trả về cặp (câu thoại trước, câu thoại sau) liên tiếp."""
        return pairwise(self.utterances)
