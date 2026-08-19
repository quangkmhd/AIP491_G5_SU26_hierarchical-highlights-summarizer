from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr


class StreamingAudioSession:
    """Persist source PCM and resample one continuous microphone timeline."""

    target_rate = 16000

    def __init__(self, session_id: str, source_rate: int, root: Path) -> None:
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
        if self._closed or self._flushed:
            raise RuntimeError("audio session is closed or flushed")
        pcm = np.asarray(samples, dtype=np.float32)
        self._writer.write(pcm)
        self.accepted_samples += len(pcm)
        return np.asarray(
            self._resampler.resample_chunk(pcm, last=False),
            dtype=np.float32,
        )

    def flush(self) -> np.ndarray:
        if self._closed or self._flushed:
            return np.empty(0, dtype=np.float32)
        self._flushed = True
        return np.asarray(
            self._resampler.resample_chunk(np.empty(0, dtype=np.float32), last=True),
            dtype=np.float32,
        )

    def close(self, *, retain: bool = True) -> Path:
        if not self._closed:
            self._writer.close()
            self._closed = True
        if not retain:
            self.path.unlink(missing_ok=True)
        return self.path


def cleanup_expired_recordings(root: Path, retention_hours: int) -> list[Path]:
    if not root.exists():
        return []
    cutoff = time.time() - retention_hours * 3600
    removed: list[Path] = []
    for path in sorted(root.glob("*.wav")):
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path)
    return removed


__all__ = ["StreamingAudioSession", "cleanup_expired_recordings"]
