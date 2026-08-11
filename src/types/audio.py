"""Versioned wire types for far-field microphone sessions."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ._base import BaseSchema


class AppliedAudioSettings(BaseSchema):
    """Browser-reported microphone processing actually applied to a track."""

    echo_cancellation: bool | None = None
    noise_suppression: bool | None = None
    auto_gain_control: bool | None = None


class AudioSessionStart(BaseSchema):
    """First control message required before binary PCM frames."""

    type: Literal["session_start"]
    protocol_version: Literal[1]
    sample_rate: int = Field(ge=8000, le=192000)
    channels: Literal[1]
    settings: AppliedAudioSettings = Field(default_factory=AppliedAudioSettings)


class AudioQualityMetrics(BaseSchema):
    """Signal measurements attached to a finalized utterance."""

    rms: float = Field(ge=0.0)
    peak: float = Field(ge=0.0)
    clipped: bool
    vad_confidence: float = Field(ge=0.0, le=1.0)
    speech_duration: float = Field(ge=0.0)


class FinalUtteranceEvent(BaseSchema):
    """Final speaker-labelled transcript emitted by the audio pipeline."""

    type: Literal["utterance"] = "utterance"
    id: int = Field(ge=1)
    session_id: str = Field(min_length=1)
    speaker: str = Field(min_length=1)
    text: str = Field(min_length=1)
    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(ge=0.0)
    source_sample_rate: int = Field(ge=8000, le=192000)
    sample_rate: Literal[16000] = 16000
    quality: AudioQualityMetrics
    preprocessing_ms: float = Field(ge=0.0)
    diarization_ms: float = Field(ge=0.0)
    asr_ms: float = Field(ge=0.0)
    total_ms: float = Field(ge=0.0)
    degraded: bool = False
    fallback: bool = False

    @model_validator(mode="after")
    def _validate_timeline(self) -> "FinalUtteranceEvent":
        if self.end_sec < self.start_sec:
            raise ValueError("end_sec must be greater than or equal to start_sec")
        return self


__all__ = [
    "AppliedAudioSettings",
    "AudioQualityMetrics",
    "AudioSessionStart",
    "FinalUtteranceEvent",
]
