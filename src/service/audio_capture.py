"""Recoverable native microphone capture with stateful high-quality resampling."""

from __future__ import annotations

import re
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr

_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _validate_pcm(samples: np.ndarray) -> np.ndarray:
    pcm = np.asarray(samples)
    if pcm.ndim != 1:
        raise ValueError("audio samples must be mono (one-dimensional)")
    if pcm.dtype != np.float32:
        raise ValueError("audio samples must use Float32 PCM")
    if not np.isfinite(pcm).all():
        raise ValueError("audio samples must contain only finite values")
    return pcm


class StreamingAudioSession:
    """Persist source PCM and resample one continuous microphone timeline."""

    target_rate = 16000

    def __init__(self, session_id: str, source_rate: int, root: Path) -> None:
        if not _SAFE_SESSION_ID.fullmatch(session_id):
            raise ValueError("session_id contains unsupported characters")
        if not 8000 <= source_rate <= 192000:
            raise ValueError("source_rate must be between 8000 and 192000 Hz")

        self.session_id = session_id
        self.source_rate = source_rate
        self.accepted_samples = 0
        self._closed = False
        self._flushed = False

        root.mkdir(parents=True, exist_ok=True)
        self.path = root / f"{session_id}.wav"
        self._writer = sf.SoundFile(
            self.path,
            mode="w",
            samplerate=source_rate,
            channels=1,
            subtype="FLOAT",
        )
        self._resampler = soxr.ResampleStream(
            source_rate,
            self.target_rate,
            1,
            dtype="float32",
            quality="HQ",
        )

    def push(self, samples: np.ndarray) -> np.ndarray:
        """Persist and resample one ordered Float32 mono frame."""
        if self._closed:
            raise RuntimeError("audio session is closed")
        if self._flushed:
            raise RuntimeError("audio session was already flushed")
        pcm = _validate_pcm(samples)
        self._writer.write(pcm)
        self.accepted_samples += len(pcm)
        return np.asarray(
            self._resampler.resample_chunk(pcm, last=False),
            dtype=np.float32,
        )

    def flush(self) -> np.ndarray:
        """Drain delayed resampler output exactly once."""
        if self._closed:
            raise RuntimeError("audio session is closed")
        if self._flushed:
            return np.empty(0, dtype=np.float32)
        self._flushed = True
        return np.asarray(
            self._resampler.resample_chunk(np.empty(0, dtype=np.float32), last=True),
            dtype=np.float32,
        )

    def close(self, *, retain: bool = True) -> Path:
        """Close the source recording and optionally delete it immediately."""
        if not self._closed:
            self._writer.close()
            self._closed = True
        if not retain:
            self.path.unlink(missing_ok=True)
        return self.path


def cleanup_expired_recordings(
    root: Path,
    retention_hours: int,
    *,
    now: float | None = None,
) -> list[Path]:
    """Delete only WAV recordings older than the configured retention period."""
    if retention_hours < 1:
        raise ValueError("retention_hours must be positive")
    if not root.exists():
        return []

    cutoff = (time.time() if now is None else now) - retention_hours * 60 * 60
    removed: list[Path] = []
    for path in sorted(root.glob("*.wav")):
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path)
    return removed


__all__ = ["StreamingAudioSession", "cleanup_expired_recordings"]
