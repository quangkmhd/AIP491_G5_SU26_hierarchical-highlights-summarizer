"""Regression tests for finalizing VAD-delimited Zipformer streams."""

from __future__ import annotations

import unittest
import sys
from types import ModuleType

import numpy as np

# The unit under test only needs the sherpa-onnx Python interface at runtime;
# loading the CUDA extension is covered by the separately invoked live check.
sys.modules.setdefault("sherpa_onnx", ModuleType("sherpa_onnx"))

from src.service.asr_engine import AsrEngine  # noqa: E402
from src.config.asr import AsrConfig  # noqa: E402


class _FakeStream:
    def __init__(self) -> None:
        self.waveforms: list[tuple[int, np.ndarray]] = []
        self.finished = False

    def accept_waveform(self, sample_rate: int, samples: np.ndarray) -> None:
        if self.finished:
            raise AssertionError("samples were appended after input_finished")
        self.waveforms.append((sample_rate, samples))

    def input_finished(self) -> None:
        self.finished = True


class _FakeRecognizer:
    def __init__(self) -> None:
        self.stream = _FakeStream()
        self.decode_calls = 0

    def create_stream(self) -> _FakeStream:
        return self.stream

    def is_ready(self, stream: _FakeStream) -> bool:
        return self.decode_calls < 2

    def decode_stream(self, stream: _FakeStream) -> None:
        self.decode_calls += 1

    def get_result(self, stream: _FakeStream) -> str:
        if not stream.finished:
            return "truncated"
        if len(stream.waveforms) != 2:
            return "truncated"
        return "final text"


class AsrEngineTests(unittest.TestCase):
    def test_default_config_uses_ssl_chunk_32_checkpoint(self) -> None:
        """Changing back to the legacy checkpoint would bypass the selected model."""
        config = AsrConfig(_env_file=None)

        self.assertIn("Zipformer-SSL-100h", config.encoder)
        self.assertIn("chunk-32-left-128", config.encoder)
        self.assertIn("Zipformer-SSL-100h", config.decoder)
        self.assertIn("chunk-32-left-128", config.decoder)
        self.assertIn("Zipformer-SSL-100h", config.joiner)
        self.assertIn("chunk-32-left-128", config.joiner)
        self.assertIn("Zipformer-SSL-100h", config.tokens)
        self.assertFalse(config.emit_partials)
        self.assertEqual(config.audio_retention_hours, 24)

    def test_decode_segment_finalizes_with_float32_zero_tail(self) -> None:
        """A missing tail or end-of-input signal must not return a final transcript."""
        engine = object.__new__(AsrEngine)
        recognizer = _FakeRecognizer()
        engine.asr_engine = recognizer
        audio = np.array([0.25, -0.25], dtype=np.float32)

        self.assertEqual(engine.decode_segment(audio), "final text")
        self.assertIs(recognizer.stream.waveforms[0][1], audio)
        tail = recognizer.stream.waveforms[1][1]
        self.assertEqual(recognizer.stream.waveforms[0][0], 16000)
        self.assertEqual(recognizer.stream.waveforms[1][0], 16000)
        self.assertEqual(tail.dtype, np.float32)
        self.assertEqual(tail.shape, (6400,))
        self.assertEqual(np.count_nonzero(tail), 0)
        self.assertTrue(recognizer.stream.finished)
        self.assertEqual(recognizer.decode_calls, 2)
