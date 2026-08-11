"""Tests for the versioned far-field audio WebSocket contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.types.audio import (
    AppliedAudioSettings,
    AudioSessionStart,
    FinalUtteranceEvent,
)


def test_session_start_accepts_supported_mono_capture() -> None:
    """Rejecting normal native-rate mono capture would prevent a meeting session."""
    start = AudioSessionStart(
        type="session_start",
        protocol_version=1,
        sample_rate=48000,
        channels=1,
        settings=AppliedAudioSettings(
            echo_cancellation=True,
            noise_suppression=True,
            auto_gain_control=True,
        ),
    )

    assert start.sample_rate == 48000
    assert start.settings.noise_suppression is True


@pytest.mark.parametrize(
    ("field", "value"),
    [("protocol_version", 2), ("channels", 2), ("sample_rate", 7999)],
)
def test_session_start_rejects_unsupported_audio_contract(field: str, value: int) -> None:
    """Accepting an unknown protocol or audio shape would corrupt PCM interpretation."""
    payload = {
        "type": "session_start",
        "protocol_version": 1,
        "sample_rate": 48000,
        "channels": 1,
        "settings": {},
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        AudioSessionStart.model_validate(payload)


def test_final_utterance_rejects_reversed_timeline() -> None:
    """A reversed interval would corrupt transcript ordering and replay alignment."""
    with pytest.raises(ValidationError, match="end_sec"):
        FinalUtteranceEvent(
            id=1,
            session_id="session-1",
            speaker="Speaker 01",
            text="xin chào",
            start_sec=2.0,
            end_sec=1.0,
            source_sample_rate=48000,
            quality={
                "rms": 0.02,
                "peak": 0.2,
                "clipped": False,
                "vad_confidence": 0.9,
                "speech_duration": 1.0,
            },
            preprocessing_ms=10,
            diarization_ms=20,
            asr_ms=30,
            total_ms=60,
        )
