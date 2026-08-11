"""Tests for chunked far-field enhancement and quality measurement."""

from __future__ import annotations

import numpy as np
import pytest

from src.service.audio_preprocessor import AudioPreprocessor, PassthroughEnhancer


class RecordingEnhancer:
    def __init__(self) -> None:
        self.calls: list[np.ndarray] = []

    def enhance(self, samples: np.ndarray) -> np.ndarray:
        self.calls.append(samples.copy())
        return samples.copy()


def test_preprocessor_emits_non_overlapping_timeline_with_overlap_context() -> None:
    """Chunk context must not duplicate samples in the downstream timeline."""
    enhancer = RecordingEnhancer()
    processor = AudioPreprocessor(
        enhancer,
        sample_rate=16000,
        chunk_seconds=2.5,
        overlap_seconds=0.3,
    )

    emitted = processor.process(np.ones(16000 * 5, dtype=np.float32) * 0.01)

    assert len(emitted) == 2
    assert [len(chunk.samples) for chunk in emitted] == [40000, 40000]
    assert [chunk.start_sample for chunk in emitted] == [0, 40000]
    assert [chunk.end_sample for chunk in emitted] == [40000, 80000]
    assert [len(call) for call in enhancer.calls] == [40000, 44800]


def test_preprocessor_measures_quiet_signal_without_hidden_gain() -> None:
    """Silently amplifying noise would make VAD calibration meaningless."""
    processor = AudioPreprocessor(
        RecordingEnhancer(),
        sample_rate=16000,
        chunk_seconds=2.5,
        overlap_seconds=0.3,
    )

    [chunk] = processor.process(np.full(40000, 0.001, dtype=np.float32))

    assert chunk.rms == pytest.approx(0.001)
    assert chunk.peak == pytest.approx(0.001)
    assert chunk.clipped is False


def test_flush_emits_only_unprocessed_tail() -> None:
    """Flushing must retain the end of speech without replaying overlap context."""
    processor = AudioPreprocessor(
        RecordingEnhancer(),
        sample_rate=16000,
        chunk_seconds=2.5,
        overlap_seconds=0.3,
    )
    processor.process(np.ones(40000, dtype=np.float32) * 0.02)
    processor.process(np.ones(8000, dtype=np.float32) * 0.03)

    [tail] = processor.flush()

    assert len(tail.samples) == 8000
    assert tail.start_sample == 40000
    assert tail.end_sample == 48000


def test_preprocessor_rejects_invalid_overlap() -> None:
    """An overlap as large as a chunk would prevent the stream from advancing."""
    with pytest.raises(ValueError, match="overlap"):
        AudioPreprocessor(
            RecordingEnhancer(),
            sample_rate=16000,
            chunk_seconds=0.3,
            overlap_seconds=0.3,
        )


def test_passthrough_enhancer_preserves_distant_speech_samples() -> None:
    """Default far-field mode must not remove speech already denoised by the browser."""
    source = np.linspace(-0.03, 0.03, 1600, dtype=np.float32)

    output = PassthroughEnhancer().enhance(source)

    assert output is not source
    assert output.dtype == np.float32
    np.testing.assert_array_equal(output, source)
