"""DialogueSample -- a single dialogue with ground-truth segments.

Convention used by data/eval_vi/*.json:
    - utterances: list of plain-text utterances (the corpus language)
    - segments: list of segment SIZES in utterances; the i-th entry is
      the number of utterances in the i-th segment. The cumulative sum
      equals len(utterances). For example, segments=[13, 5, 4] on a
      22-utterance dialogue means 3 segments of sizes 13, 5, 4.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field, model_validator

from src.types._base import BaseSchema


class DialogueSample(BaseSchema):
    """A single dialogue loaded from an evaluation corpus file."""

    dial_id: int = Field(ge=0, description="Dialogue identifier (non-negative).")
    utterances: list[str] = Field(
        ...,
        min_length=2,
        description="Ordered list of utterance texts (the corpus language).",
    )
    segments: list[int] = Field(
        default_factory=list,
        description="List of segment SIZES in utterances; cumulative sum = utterance_count.",
    )
    set: str = Field(
        default="test",
        description="Split: 'train' | 'dev' | 'test'.",
    )
    utterances_vi: Optional[list[str]] = Field(
        default=None,
        description="Vietnamese translation (if available).",
    )
    utterances_en: Optional[list[str]] = Field(
        default=None,
        description="English translation (if available).",
    )

    @model_validator(mode="after")
    def _validate_segments(self) -> "DialogueSample":
        if self.segments:
            if any(s <= 0 for s in self.segments):
                raise ValueError(
                    f"Segment sizes must be positive; got {self.segments}"
                )
            if sum(self.segments) != self.utterance_count:
                raise ValueError(
                    f"Sum of segment sizes ({sum(self.segments)}) does not match "
                    f"utterance count ({self.utterance_count})"
                )
        return self

    @property
    def utterance_count(self) -> int:
        return len(self.utterances)

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    @property
    def segment_sizes(self) -> list[int]:
        """Return the size of each segment in utterances."""
        return list(self.segments) if self.segments else [self.utterance_count]

    @property
    def median_segment_length(self) -> int:
        """Median segment length in utterances (used as the k window for P_k)."""
        sizes = self.segment_sizes
        sorted_sizes = sorted(sizes)
        n = len(sorted_sizes)
        if n % 2 == 0:
            return (sorted_sizes[n // 2 - 1] + sorted_sizes[n // 2]) // 2
        return sorted_sizes[n // 2]
