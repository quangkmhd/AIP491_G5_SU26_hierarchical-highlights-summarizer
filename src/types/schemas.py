from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, Field

from .hierarchical_summary import HierarchicalSummary, MeetingStatus
from .transcript import DialogueTranscript
from .utterance import Utterance


class TranscriptIngestionRequest(BaseModel):
    """Payload accepted by `POST /api/v1/meetings/process`."""

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

    def materialize(self) -> DialogueTranscript:
        """Chuyển đổi yêu cầu nạp bản ghi thành đối tượng DialogueTranscript."""
        has_utterances = bool(self.utterances)
        has_flat = bool(self.flat_texts)
        if has_utterances and has_flat:
            raise ValueError("Provide either `utterances` or `flat_texts`, not both.")
        if not has_utterances and not has_flat:
            raise ValueError("Provide at least one of `utterances` or `flat_texts`.")

        if self.flat_texts:
            utterances = [
                Utterance(speaker=f"S{i + 1}", text=t, index=i)
                for i, t in enumerate(self.flat_texts)
            ]
        else:
            utterances = list(self.utterances)

        return DialogueTranscript(
            utterances=utterances,
            meeting_title=self.meeting_title,
            metadata={"language": self.language, **self.metadata},
        )


class MeetingProcessResponse(BaseModel):
    """Response returned by `POST /api/v1/meetings/process`."""

    meeting_id: str
    status: MeetingStatus
    summary: Optional[HierarchicalSummary] = None
    error: Optional[str] = None
