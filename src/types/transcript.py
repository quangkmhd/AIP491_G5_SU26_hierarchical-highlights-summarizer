from __future__ import annotations

from datetime import datetime, timezone
from itertools import pairwise
from typing import ClassVar, Iterator, Optional
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from ._base import BaseSchema
from .utterance import Utterance


class DialogueTranscript(BaseSchema):
    """An ordered sequence of utterances representing a full meeting transcript.

    Attributes:
        utterances: Ordered list of Utterance objects.
        meeting_title: Optional human-readable title for the meeting.
        metadata: Arbitrary key-value metadata attached to the transcript.
        transcript_id: Unique identifier for this transcript submission.
    """

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

    # ClassVar so the limit is a true constant, not a per-instance field.
    # 5000 is the recommended ceiling for synchronous TextTiling runs; longer
    # meetings must be processed asynchronously (see docs/design-docs/models-and-roadmap.md).
    MAX_UTTERANCES: ClassVar[int] = 5000

    @model_validator(mode="after")
    def _validate_transcript(self) -> "DialogueTranscript":
        if len(self.utterances) > self.MAX_UTTERANCES:
            raise ValueError(
                f"DialogueTranscript has {len(self.utterances)} utterances, "
                f"exceeds MAX_UTTERANCES={self.MAX_UTTERANCES}. "
                "Process longer meetings asynchronously."
            )
        expected = list(range(len(self.utterances)))
        actual = [u.index for u in self.utterances]
        if actual != expected:
            raise ValueError(
                "Utterance indices must be a contiguous 0..N-1 sequence "
                f"(got {actual[:5]}{'...' if len(actual) > 5 else ''})."
            )
        return self

    @property
    def utterance_count(self) -> int:
        return len(self.utterances)

    @property
    def utterance_pairs(self) -> Iterator[tuple[Utterance, Utterance]]:
        """Yield consecutive (prev, next) utterance pairs for coherence scoring."""
        return pairwise(self.utterances)
