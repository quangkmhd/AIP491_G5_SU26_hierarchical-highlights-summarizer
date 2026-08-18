from __future__ import annotations

from typing import Any

import numpy as np

from .diarization_engine import SpeakerProfile


class NoOverlapDetector:
    """Conservative adapter used when an overlap model is not configured."""

    def detect(self, samples: np.ndarray) -> bool:
        return False


class NoSourceSeparator:
    """Fail explicitly if overlap is detected without a configured separator."""

    def separate(
        self,
        samples: np.ndarray,
        profiles: tuple[SpeakerProfile, ...],
    ) -> list[np.ndarray]:
        raise RuntimeError("overlap source separation is not configured")


class SherpaSpeakerEmbedder:
    """Adapt sherpa-onnx SpeakerEmbeddingExtractor to the domain protocol."""

    def __init__(self, extractor: Any, sample_rate: int = 16000) -> None:
        self.extractor = extractor
        self.sample_rate = sample_rate

    def extract(self, samples: np.ndarray) -> np.ndarray:
        stream = self.extractor.create_stream()
        stream.accept_waveform(self.sample_rate, samples)
        stream.input_finished()
        return np.asarray(self.extractor.compute(stream), dtype=np.float32).reshape(-1)


class PyannoteOverlapDetector:
    """Adapt a configured pyannote inference callable to overlap decisions."""

    def __init__(self, inference: Any, onset: float = 0.55) -> None:
        self.inference = inference
        self.onset = onset

    def detect(self, samples: np.ndarray) -> bool:
        output = self.inference(samples)
        data = np.asarray(getattr(output, "data", output))
        if data.ndim < 2:
            raise ValueError("overlap model must return frame-by-speaker scores")
        return bool(np.any(np.sum(data > self.onset, axis=1) >= 2))


class PipelineSourceSeparator:
    """Adapt existing TSE/BSS components without permitting mock audio."""

    def __init__(self, target_separator: Any, blind_separator: Any) -> None:
        self.target_separator = target_separator
        self.blind_separator = blind_separator

    def separate(
        self,
        samples: np.ndarray,
        profiles: tuple[SpeakerProfile, ...],
    ) -> list[np.ndarray]:
        if len(profiles) >= 2:
            legacy_profiles = tuple(
                {
                    "embedding": profile.centroid,
                    "reference_audio": profile.reference_audio,
                }
                for profile in profiles[:2]
            )
            results = self.target_separator.extract_targets(samples, *legacy_profiles)
            streams = [
                np.asarray(audio, dtype=np.float32)
                for audio, valid in results
                if valid
            ]
        else:
            streams = [
                np.asarray(audio, dtype=np.float32)
                for audio in self.blind_separator.separate(samples)
            ]
        if not streams:
            raise RuntimeError("speaker separation returned no valid streams")
        return streams


__all__ = [
    "NoOverlapDetector",
    "NoSourceSeparator",
    "PipelineSourceSeparator",
    "PyannoteOverlapDetector",
    "SherpaSpeakerEmbedder",
]
