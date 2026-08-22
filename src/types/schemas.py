from __future__ import annotations

from pydantic import BaseModel, Field

from .transcript import DialogueTranscript
from .utterance import Utterance

__all__ = [
    "TranscriptIngestionRequest",
]


class TranscriptIngestionRequest(BaseModel):
    """Payload accepted by `POST /api/v1/meetings/process`."""

    utterances: list[Utterance] = Field(
        ...,
        description="Danh sách các câu thoại Utterance của cuộc họp.",
    )
    language: str = Field(
        default="vi",
        description="Ngôn ngữ bản ghi cuộc họp (ví dụ 'vi').",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Thông tin metadata đính kèm.",
    )

    def materialize(self) -> DialogueTranscript:
        """Chuyển đổi yêu cầu nạp bản ghi thành đối tượng DialogueTranscript."""
        return DialogueTranscript(
            utterances=self.utterances,
            metadata={"language": self.language, **self.metadata},
        )
