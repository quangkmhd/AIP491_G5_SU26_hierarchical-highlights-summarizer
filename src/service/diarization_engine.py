from __future__ import annotations

import logging
import time
from typing import Any, Protocol

import numpy as np

logger = logging.getLogger("src.service.diarization_engine")


class OverlapDetector(Protocol):
    def detect(self, samples: np.ndarray) -> bool: ...


class SpeakerEmbedder(Protocol):
    def extract(self, samples: np.ndarray) -> np.ndarray: ...


class SherpaSpeakerEmbedder:
    """Adapt sherpa-onnx SpeakerEmbeddingExtractor to extract speaker embeddings."""

    def __init__(self, extractor: Any, sample_rate: int = 16000) -> None:
        self.extractor = extractor
        self.sample_rate = sample_rate

    def extract(self, samples: np.ndarray) -> np.ndarray:
        stream = self.extractor.create_stream()
        stream.accept_waveform(self.sample_rate, samples)
        stream.input_finished()
        return np.asarray(self.extractor.compute(stream), dtype=np.float32).reshape(-1)


class SourceSeparator(Protocol):
    def separate(
        self,
        samples: np.ndarray,
        profiles: tuple["SpeakerProfile", ...],
    ) -> list[np.ndarray]: ...


class SpeakerProfile:
    def __init__(
        self,
        speaker: str,
        centroid: np.ndarray,
        observations: int,
        reference_audio: np.ndarray,
    ) -> None:
        self.speaker = speaker
        self.centroid = centroid
        self.observations = observations
        self.reference_audio = reference_audio

    def update(self, embedding: np.ndarray, reference_audio: np.ndarray) -> None:
        """Update a bounded running centroid so old meetings do not freeze a profile."""
        weight = min(self.observations, 9)
        merged = (self.centroid * weight + embedding) / (weight + 1)
        norm = float(np.linalg.norm(merged))
        if norm > 1e-6:
            self.centroid = (merged / norm).astype(np.float32, copy=False)
        self.observations += 1
        self.reference_audio = reference_audio.copy()


class DiarizedStream:
    def __init__(self, speaker: str, samples: np.ndarray, fallback: bool = False) -> None:
        self.speaker = speaker
        self.samples = samples
        self.fallback = fallback


class DiarizationResult:
    def __init__(
        self,
        streams: tuple[DiarizedStream, ...],
        has_overlap: bool,
        latency_ms: float,
    ) -> None:
        self.streams = streams
        self.has_overlap = has_overlap
        self.latency_ms = latency_ms


class DiarizationEngine:
    """Identify sequential speakers and isolate failures at the overlap boundary."""

    def __init__(
        self,
        embedder: SpeakerEmbedder,
        overlap_detector: OverlapDetector | None = None,
        separator: SourceSeparator | None = None,
        *,
        matching_threshold: float = 0.65,
        profile_min_duration: float = 1.5,
        profile_min_confidence: float = 0.9,
    ) -> None:
        if not 0.0 <= matching_threshold <= 1.0:
            raise ValueError("matching_threshold must be between 0 and 1")
        self.overlap_detector = overlap_detector
        self.embedder = embedder
        self.separator = separator
        self.matching_threshold = matching_threshold
        self.profile_min_duration = profile_min_duration
        self.profile_min_confidence = profile_min_confidence
        self.profiles: list[SpeakerProfile] = []

    def profile_count(self) -> int:
        return len(self.profiles)

    def process(
        self,
        enhanced_audio: np.ndarray,
        speaker_audio: np.ndarray,
        *,
        speech_duration: float,
        vad_confidence: float,
    ) -> DiarizationResult:
        started = time.perf_counter()
        has_overlap = bool(self.overlap_detector.detect(speaker_audio)) if self.overlap_detector else False
        if has_overlap and self.separator:
            try:
                separated = self.separator.separate(
                    enhanced_audio,
                    tuple(self.profiles),
                )
                streams = tuple(
                    self._identify(
                        stream,
                        stream,
                        speech_duration=len(stream) / 16000,
                        vad_confidence=vad_confidence,
                    )
                    for stream in separated
                    if self._valid_audio(stream)
                )
                if not streams:
                    raise ValueError("source separator returned no valid streams")
            except Exception as exc:  # noqa: BLE001 - this boundary must retain speech
                logger.warning("Diarization overlap fallback: %s", exc)
                streams = (DiarizedStream("Unknown Speaker", enhanced_audio.copy(), True),)
        else:
            streams = (
                self._identify(
                    enhanced_audio,
                    speaker_audio,
                    speech_duration=speech_duration,
                    vad_confidence=vad_confidence,
                ),
            )

        return DiarizationResult(
            streams=streams,
            has_overlap=has_overlap,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _identify(
        self,
        output_audio: np.ndarray,
        embedding_audio: np.ndarray,
        *,
        speech_duration: float,
        vad_confidence: float,
    ) -> DiarizedStream:
        embedding = self._normalize(self.embedder.extract(embedding_audio))
        if embedding is None:
            return DiarizedStream("Unknown Speaker", output_audio.copy())

        matched = self._best_match(embedding)
        good_reference = (
            speech_duration >= self.profile_min_duration
            and vad_confidence >= self.profile_min_confidence
        )
        if matched is None:
            if not good_reference:
                return DiarizedStream("Unknown Speaker", output_audio.copy())
            matched = SpeakerProfile(
                speaker=f"Speaker {len(self.profiles) + 1:02d}",
                centroid=embedding,
                observations=1,
                reference_audio=embedding_audio.copy(),
            )
            self.profiles.append(matched)
        elif good_reference:
            matched.update(embedding, embedding_audio)
        return DiarizedStream(matched.speaker, output_audio.copy())

    def _best_match(self, embedding: np.ndarray) -> SpeakerProfile | None:
        best: SpeakerProfile | None = None
        best_score = -1.0
        for profile in self.profiles:
            score = float(np.dot(embedding, profile.centroid))
            if score > best_score:
                best = profile
                best_score = score
        return best if best_score >= self.matching_threshold else None

    def _normalize(self, embedding: np.ndarray) -> np.ndarray | None:
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if not len(vector) or not np.isfinite(vector).all():
            return None
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-6:
            return None
        return (vector / norm).astype(np.float32, copy=False)

    def _valid_audio(self, samples: np.ndarray) -> bool:
        audio = np.asarray(samples)
        return (
            audio.ndim == 1
            and audio.dtype == np.float32
            and len(audio) > 0
            and bool(np.isfinite(audio).all())
        )


__all__ = [
    "DiarizationEngine",
    "DiarizationResult",
    "DiarizedStream",
    "OverlapDetector",
    "SourceSeparator",
    "SpeakerEmbedder",
    "SpeakerProfile",
]
