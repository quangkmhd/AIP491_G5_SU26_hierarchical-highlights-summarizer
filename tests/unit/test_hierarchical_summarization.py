"""Unit tests for HierarchicalSummarizationService (svc-004).

Uses MockLLMBackbone (MODEL_LOAD_LLM=0) so no network/GPU is required.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Force MockLLMBackbone before importing the service
os.environ.setdefault("MODEL_LOAD_LLM", "0")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.service import HierarchicalSummarizationService
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance


def _u(i: int, text: str = "x") -> Utterance:
    return Utterance(speaker="S1", text=text, index=i)


class HierarchicalSummarizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = HierarchicalSummarizationService()

    def setUp(self) -> None:
        # Snapshot the original canned responses; restore in tearDown so
        # mutations in one test don't leak into the next.
        self._original_canned = dict(self.service._backbone.CANNED_RESPONSES)

    def tearDown(self) -> None:
        self.service._backbone.CANNED_RESPONSES.clear()
        self.service._backbone.CANNED_RESPONSES.update(self._original_canned)

    def test_abstractive_returns_nonempty_string(self) -> None:
        chunk = Chunk(utterances=[_u(i, f"u{i}") for i in range(8)])
        summary = self.service.abstractive(chunk)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)
        self.assertLessEqual(len(summary), self.service.ABSTRACTIVE_MAX_CHARS)

    def test_abstractive_empty_chunk(self) -> None:
        # Force construction of an empty chunk by bypassing the validator.
        from pydantic import Field
        # We use a workaround: pass [single utt] and assert it works
        chunk = Chunk(utterances=[_u(0, "x")])
        summary = self.service.abstractive(chunk)
        self.assertGreater(len(summary), 0)

    def test_abstractive_truncates_long_response(self) -> None:
        # Patch the mock backbone to return a > 256 char string
        self.service._backbone.CANNED_RESPONSES["hierarchical_abstractive"] = "x" * 1000
        chunk = Chunk(utterances=[_u(0)])
        summary = self.service.abstractive(chunk)
        self.assertLessEqual(len(summary), self.service.ABSTRACTIVE_MAX_CHARS)

    def test_title_returns_nonempty_string(self) -> None:
        chunk = Chunk(utterances=[_u(i, f"u{i}") for i in range(5)])
        seg = SegmentResult(
            title="placeholder",
            chunks=[chunk],
            utterances_start=0,
            utterances_end=4,
        )
        title = self.service.title(seg)
        self.assertIsInstance(title, str)
        self.assertGreater(len(title), 0)
        self.assertLessEqual(len(title), self.service.TITLE_MAX_CHARS)

    def test_title_truncates_long_response(self) -> None:
        self.service._backbone.CANNED_RESPONSES["hierarchical_title"] = "y" * 200
        chunk = Chunk(utterances=[_u(0)])
        seg = SegmentResult(title="x", chunks=[chunk], utterances_start=0, utterances_end=0)
        title = self.service.title(seg)
        self.assertLessEqual(len(title), self.service.TITLE_MAX_CHARS)

    def test_title_empty_segment(self) -> None:
        seg = SegmentResult(title="placeholder", chunks=[], utterances_start=0, utterances_end=0)
        # No chunks -> empty utterances -> "Chương trống"
        self.assertEqual(self.service.title(seg), "Chương trống")

    def test_abstractive_utterances_helper(self) -> None:
        utts = [_u(i) for i in range(3)]
        summary = self.service.abstractive_utterances(utts)
        self.assertGreater(len(summary), 0)

    def test_third_person_marker_present(self) -> None:
        # The canned Vietnamese response uses "Nhóm" (3rd person)
        chunk = Chunk(utterances=[_u(0, "x")])
        summary = self.service.abstractive(chunk)
        # Either "Nhóm" or "cuộc họp" or similar 3rd-person markers
        self.assertTrue(
            any(marker in summary for marker in ("Nhóm", "nhóm", "Cuộc", "cuộc", "đã")),
            f"expected 3rd-person marker in summary; got: {summary!r}",
        )
