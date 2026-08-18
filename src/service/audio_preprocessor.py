from __future__ import annotations

import time
from dataclasses import dataclass
from types import ModuleType
from typing import Protocol
import sys

import numpy as np


class AudioPreprocessingUnavailable(RuntimeError):
    """Raised when accuracy-mode enhancement cannot be initialized."""


class Enhancer(Protocol):
    """Narrow audio-enhancement boundary used by the streaming pipeline."""

    def enhance(self, samples: np.ndarray) -> np.ndarray:
        """Return an enhanced array with the same sample count."""


class PassthroughEnhancer:
    """Preserve browser-processed speech when a second denoiser is not beneficial."""

    def enhance(self, samples: np.ndarray) -> np.ndarray:
        return np.asarray(samples, dtype=np.float32).copy()


@dataclass
class ProcessedAudioChunk:
    samples: np.ndarray
    start_sample: int
    end_sample: int
    rms: float
    peak: float
    clipped: bool
    preprocessing_ms: float


class AudioPreprocessor:
    """Enhance a continuous 16 kHz stream without duplicating its timeline."""

    def __init__(
        self,
        enhancer: Enhancer,
        sample_rate: int = 16000,
        chunk_seconds: float = 2.5,
        overlap_seconds: float = 0.3,
    ) -> None:
        self.enhancer = enhancer
        self.sample_rate = sample_rate
        self.chunk_samples = round(sample_rate * chunk_seconds)
        self.overlap_samples = round(sample_rate * overlap_seconds)
        if self.chunk_samples <= 0:
            raise ValueError("chunk duration must be positive")
        if self.overlap_samples < 0 or self.overlap_samples >= self.chunk_samples:
            raise ValueError("overlap must be non-negative and shorter than a chunk")

        self._buffer = np.empty(0, dtype=np.float32)
        self._emitted_samples = 0
        self._started = False
        self._flushed = False

    def process(self, samples: np.ndarray) -> list[ProcessedAudioChunk]:
        """Accept resampled PCM and emit every complete enhanced chunk."""
        if self._flushed:
            raise RuntimeError("audio preprocessor was already flushed")
        pcm = self._validate(samples)
        if pcm.size:
            self._buffer = np.concatenate((self._buffer, pcm))

        output: list[ProcessedAudioChunk] = []
        if not self._started and len(self._buffer) >= self.chunk_samples:
            window = self._buffer[: self.chunk_samples]
            output.append(self._enhance_window(window, trim_left=0))
            self._buffer = self._buffer[self.chunk_samples - self.overlap_samples :]
            self._started = True

        required = self.chunk_samples + self.overlap_samples
        while self._started and len(self._buffer) >= required:
            window = self._buffer[:required]
            output.append(self._enhance_window(window, trim_left=self.overlap_samples))
            self._buffer = self._buffer[self.chunk_samples :]
        return output

    def flush(self) -> list[ProcessedAudioChunk]:
        """Emit only samples not already represented downstream."""
        if self._flushed:
            return []
        self._flushed = True
        if not self._started:
            if not len(self._buffer):
                return []
            chunk = self._enhance_window(self._buffer, trim_left=0)
        else:
            if len(self._buffer) <= self.overlap_samples:
                self._buffer = np.empty(0, dtype=np.float32)
                return []
            chunk = self._enhance_window(self._buffer, trim_left=self.overlap_samples)
        self._buffer = np.empty(0, dtype=np.float32)
        return [chunk]

    def _enhance_window(self, window: np.ndarray, trim_left: int) -> ProcessedAudioChunk:
        started = time.perf_counter()
        enhanced = np.asarray(self.enhancer.enhance(window.copy()), dtype=np.float32)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if enhanced.ndim != 1 or len(enhanced) != len(window):
            raise ValueError("enhancer must preserve mono shape and sample count")
        if not np.isfinite(enhanced).all():
            raise ValueError("enhancer returned non-finite audio")

        samples = enhanced[trim_left:].copy()
        start = self._emitted_samples
        self._emitted_samples += len(samples)
        magnitude = np.abs(samples)
        rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))) if len(samples) else 0.0
        peak = float(np.max(magnitude)) if len(samples) else 0.0
        return ProcessedAudioChunk(
            samples=samples,
            start_sample=start,
            end_sample=self._emitted_samples,
            rms=rms,
            peak=peak,
            clipped=bool(np.any(magnitude >= 0.999)),
            preprocessing_ms=elapsed_ms,
        )

    @staticmethod
    def _validate(samples: np.ndarray) -> np.ndarray:
        pcm = np.asarray(samples)
        if pcm.ndim != 1 or pcm.dtype != np.float32:
            raise ValueError("preprocessor expects mono Float32 PCM")
        if not np.isfinite(pcm).all():
            raise ValueError("preprocessor expects finite PCM")
        return pcm


class DeepFilterNetEnhancer:
    """Lazy DeepFilterNet3 adapter for 16 kHz meeting audio."""

    def __init__(self, atten_lim_db: float = 15.0, post_filter: bool = False) -> None:
        try:
            import torch
            import torchaudio
            _install_torchaudio_backend_compat(torchaudio)
            from df.enhance import enhance, init_df
        except ImportError as exc:
            raise AudioPreprocessingUnavailable(
                "DeepFilterNet is required when ASR accuracy mode is enabled"
            ) from exc

        self._torch = torch
        self._torchaudio = torchaudio
        self._enhance_fn = enhance
        self._model, self._state, _ = init_df(post_filter=post_filter)
        self._atten_lim_db = atten_lim_db
        self._model_rate = int(self._state.sr())

    def enhance(self, samples: np.ndarray) -> np.ndarray:
        source = self._torch.from_numpy(samples).float().unsqueeze(0)
        at_model_rate = self._torchaudio.functional.resample(source, 16000, self._model_rate)
        with self._torch.inference_mode():
            cleaned = self._enhance_fn(
                self._model,
                self._state,
                at_model_rate,
                atten_lim_db=self._atten_lim_db,
            )
        at_16k = self._torchaudio.functional.resample(cleaned, self._model_rate, 16000)
        output = at_16k.squeeze(0).detach().cpu().numpy().astype(np.float32, copy=False)
        if len(output) > len(samples):
            output = output[: len(samples)]
        elif len(output) < len(samples):
            output = np.pad(output, (0, len(samples) - len(output)))
        return output


def _install_torchaudio_backend_compat(torchaudio_module: object) -> None:
    """Provide the type-only namespace DeepFilterNet 0.5 imports on torchaudio 2.11."""
    try:
        from torchaudio.backend.common import AudioMetaData as _AudioMetaData  # noqa: F401
        return
    except ImportError:
        pass

    class AudioMetaData:
        """Compatibility type used only by DeepFilterNet file-I/O annotations."""

    backend = ModuleType("torchaudio.backend")
    common = ModuleType("torchaudio.backend.common")
    common.AudioMetaData = AudioMetaData  # type: ignore[attr-defined]
    backend.common = common  # type: ignore[attr-defined]
    setattr(torchaudio_module, "backend", backend)
    sys.modules["torchaudio.backend"] = backend
    sys.modules["torchaudio.backend.common"] = common


__all__ = [
    "AudioPreprocessingUnavailable",
    "AudioPreprocessor",
    "DeepFilterNetEnhancer",
    "Enhancer",
    "PassthroughEnhancer",
    "ProcessedAudioChunk",
]
