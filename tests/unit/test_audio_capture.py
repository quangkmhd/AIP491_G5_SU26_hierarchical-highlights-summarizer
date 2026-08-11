"""Tests for recoverable native audio capture and streaming resampling."""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from src.service.audio_capture import (
    StreamingAudioSession,
    cleanup_expired_recordings,
)


def test_streaming_session_preserves_duration_and_writes_source_wav(tmp_path: Path) -> None:
    """Resetting a resampler per WebSocket frame would lose or duplicate samples."""
    timeline = np.arange(48000, dtype=np.float32) / 48000
    source = (0.2 * np.sin(2 * np.pi * 440 * timeline)).astype(np.float32)
    session = StreamingAudioSession("session-1", 48000, tmp_path)

    outputs = [session.push(chunk) for chunk in np.array_split(source, 17)]
    outputs.append(session.flush())
    resampled = np.concatenate(outputs)
    wav_path = session.close(retain=True)

    assert abs(len(resampled) - 16000) <= 2
    stored, stored_rate = sf.read(wav_path, dtype="float32")
    assert stored_rate == 48000
    np.testing.assert_allclose(stored, source, atol=1e-6)
    assert session.accepted_samples == 48000


def test_streaming_session_rejects_invalid_pcm_before_writing(tmp_path: Path) -> None:
    """Non-finite PCM must not contaminate the recovery WAV."""
    session = StreamingAudioSession("session-2", 16000, tmp_path)

    try:
        session.push(np.array([0.1, np.nan], dtype=np.float32))
    except ValueError as exc:
        assert "finite" in str(exc)
    else:
        raise AssertionError("invalid PCM was accepted")

    assert session.accepted_samples == 0
    session.close(retain=False)


def test_cleanup_only_removes_expired_recordings(tmp_path: Path) -> None:
    """Retention cleanup must not delete a fresh or unrelated file."""
    expired = tmp_path / "expired.wav"
    fresh = tmp_path / "fresh.wav"
    unrelated = tmp_path / "notes.txt"
    for path in (expired, fresh, unrelated):
        path.write_bytes(b"data")
    old = time.time() - 25 * 60 * 60
    os.utime(expired, (old, old))
    os.utime(unrelated, (old, old))

    removed = cleanup_expired_recordings(tmp_path, retention_hours=24)

    assert removed == [expired]
    assert not expired.exists()
    assert fresh.exists()
    assert unrelated.exists()
