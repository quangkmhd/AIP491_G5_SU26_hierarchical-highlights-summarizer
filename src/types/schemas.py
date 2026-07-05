"""API request/response schemas for the FastAPI runtime.

These schemas are intentionally separate from the domain types so the wire
contract can evolve independently of the core data structures. They reuse the
shared types so round-trips stay type-safe.

Note (model-001+, D1): `HighlightUpsertRequest` was removed because the
Highlights (DR1) product surface is out of scope.
"""

from __future__ import annotations

from typing import Annotated, Optional

from pydantic import Field, model_validator

from ._base import BaseSchema
# Highlight family removed in model-001+ (DR1 dropped from scope).
from .hierarchical_recap import HierarchicalRecap, MeetingStatus
from .transcript import DialogueTranscript
from .utterance import Utterance

__all__ = [
    "TranscriptIngestionRequest",
    "MeetingProcessResponse",
]


class TranscriptIngestionRequest(BaseSchema):
    """Payload accepted by `POST /api/v1/meetings/process`.

    The caller may submit either a flat list of utterance texts (the common
    case for transcripts without speaker labels) or a list of pre-built
    `Utterance` objects when speaker information is available. Exactly one
    of the two must be provided.
    """

    meeting_title: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Optional human-readable title for the meeting.",
    )
    utterances: list[Utterance] = Field(
        default_factory=list,
        description="Optional list of pre-built Utterance objects.",
    )
    flat_texts: list[Annotated[str, Field(min_length=1, max_length=4000)]] = Field(
        default_factory=list,
        description="Optional list of plain utterance strings (no speaker info).",
    )
    language: str = Field(
        default="en",
        min_length=2,
        max_length=8,
        pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?$",
        description="BCP-47 language tag for the transcript (e.g. 'en', 'vi').",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        max_length=32,
        description="Optional key-value metadata.",
    )

    @model_validator(mode="after")
    def _validate_payload(self) -> "TranscriptIngestionRequest":
        has_utterances = bool(self.utterances)
        has_flat = bool(self.flat_texts)
        if has_utterances and has_flat:
            raise ValueError(
                "Provide either `utterances` or `flat_texts`, not both."
            )
        if not has_utterances and not has_flat:
            raise ValueError(
                "Provide at least one of `utterances` or `flat_texts`."
            )
        return self

    def materialize(self) -> DialogueTranscript:
        """Materialize this request into a domain `DialogueTranscript`.

        Enforces `DialogueTranscript.MAX_UTTERANCES` so an over-sized payload
        is rejected with a clear message at the API boundary.
        """
        if self.flat_texts:
            utterances = [
                Utterance(speaker=f"S{i + 1}", text=t, index=i)
                for i, t in enumerate(self.flat_texts)
            ]
        else:
            utterances = list(self.utterances)

        if len(utterances) > DialogueTranscript.MAX_UTTERANCES:
            raise ValueError(
                f"Request contains {len(utterances)} utterances, "
                f"exceeds MAX_UTTERANCES={DialogueTranscript.MAX_UTTERANCES}. "
                "Submit the meeting asynchronously via the async job endpoint."
            )

        return DialogueTranscript(
            utterances=utterances,
            meeting_title=self.meeting_title,
            metadata={"language": self.language, **self.metadata},
        )


class MeetingProcessResponse(BaseSchema):
    """Response returned by `POST /api/v1/meetings/process`."""

    meeting_id: str
    status: MeetingStatus
    recap: Optional[HierarchicalRecap] = None
    error: Optional[str] = None
