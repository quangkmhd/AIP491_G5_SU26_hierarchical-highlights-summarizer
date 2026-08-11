"""Tests for stable speaker profiles and lossless diarization fallback."""

from __future__ import annotations

import numpy as np

from src.service.diarization_engine import DiarizationEngine


class SequenceEmbedder:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self._embeddings = iter(embeddings)

    def extract(self, samples: np.ndarray) -> np.ndarray:
        return np.asarray(next(self._embeddings), dtype=np.float32)


class NeverOverlap:
    def detect(self, samples: np.ndarray) -> bool:
        return False


class AlwaysOverlap:
    def detect(self, samples: np.ndarray) -> bool:
        return True


class UnusedSeparator:
    def separate(self, samples: np.ndarray, profiles: tuple[object, ...]) -> list[np.ndarray]:
        raise AssertionError("separator should not run for non-overlapping speech")


class FailingSeparator:
    def separate(self, samples: np.ndarray, profiles: tuple[object, ...]) -> list[np.ndarray]:
        raise RuntimeError("separation unavailable")


def _audio(value: float = 0.02) -> np.ndarray:
    return np.full(32000, value, dtype=np.float32)


def test_same_speaker_updates_centroid_instead_of_creating_new_id() -> None:
    """Replacing profiles per segment would fragment one participant into many IDs."""
    engine = DiarizationEngine(
        overlap_detector=NeverOverlap(),
        embedder=SequenceEmbedder([[1.0, 0.0], [0.98, 0.02]]),
        separator=UnusedSeparator(),
        matching_threshold=0.5,
    )

    first = engine.process(_audio(), _audio(), speech_duration=2.0, vad_confidence=0.95)
    second = engine.process(_audio(), _audio(), speech_duration=2.0, vad_confidence=0.95)

    assert first.streams[0].speaker == "Speaker 01"
    assert second.streams[0].speaker == "Speaker 01"
    assert engine.profile_count == 1
    assert engine.profiles[0].observations == 2


def test_low_quality_segment_is_matched_but_does_not_modify_profile() -> None:
    """Noisy short speech must not poison a stable reference embedding."""
    engine = DiarizationEngine(
        overlap_detector=NeverOverlap(),
        embedder=SequenceEmbedder([[1.0, 0.0], [0.99, 0.01]]),
        separator=UnusedSeparator(),
        matching_threshold=0.5,
    )
    engine.process(_audio(), _audio(), speech_duration=2.0, vad_confidence=0.95)

    result = engine.process(_audio(), _audio(), speech_duration=0.5, vad_confidence=0.6)

    assert result.streams[0].speaker == "Speaker 01"
    assert engine.profiles[0].observations == 1


def test_overlap_failure_preserves_mixed_audio_as_unknown_speaker() -> None:
    """A separation failure must never erase recognizable mixed speech."""
    source = _audio()
    engine = DiarizationEngine(
        overlap_detector=AlwaysOverlap(),
        embedder=SequenceEmbedder([[1.0, 0.0]]),
        separator=FailingSeparator(),
        matching_threshold=0.5,
    )

    result = engine.process(source, source, speech_duration=2.0, vad_confidence=0.9)

    assert result.has_overlap is True
    assert result.streams[0].speaker == "Unknown Speaker"
    assert result.streams[0].fallback is True
    np.testing.assert_array_equal(result.streams[0].samples, source)


def test_zero_embedding_returns_unknown_without_creating_profile() -> None:
    """Registering an invalid embedding would make future cosine scores undefined."""
    engine = DiarizationEngine(
        overlap_detector=NeverOverlap(),
        embedder=SequenceEmbedder([[0.0, 0.0]]),
        separator=UnusedSeparator(),
        matching_threshold=0.5,
    )

    result = engine.process(_audio(), _audio(), speech_duration=2.0, vad_confidence=0.95)

    assert result.streams[0].speaker == "Unknown Speaker"
    assert engine.profile_count == 0
