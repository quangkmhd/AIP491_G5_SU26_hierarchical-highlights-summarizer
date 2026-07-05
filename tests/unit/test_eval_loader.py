"""Unit tests for the EvalLoader (data-001)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.data import Corpus, CorpusMetadata, DialogueSample, EvalLoader, LoadResult
from src.data.eval_loader import DataLoaderError

DATA_ROOT = ROOT / "data" / "eval_vi"


class CorpusMetadataTests(unittest.TestCase):
    def test_metadata_for_all_known_corpora(self) -> None:
        for corpus in Corpus:
            meta = CorpusMetadata(corpus)
            self.assertIn(meta.language, {"en", "vi"})
            self.assertGreater(len(meta.source), 5)

    def test_meeting_committee_is_vietnamese(self) -> None:
        meta = CorpusMetadata(Corpus.MEETING_COMMITTEE)
        self.assertEqual(meta.language, "vi")
        self.assertEqual(meta.domain, "meeting")


class DialogueSampleTests(unittest.TestCase):
    def test_minimal_sample(self) -> None:
        s = DialogueSample(dial_id=0, utterances=["a", "b"], segments=[2])
        self.assertEqual(s.utterance_count, 2)
        self.assertEqual(s.segment_count, 1)
        self.assertEqual(s.segment_sizes, [2])
        self.assertEqual(s.median_segment_length, 2)

    def test_segment_sizes_3_segments(self) -> None:
        # 22 utterances, 3 segments of sizes 13, 5, 4
        s = DialogueSample(dial_id=0, utterances=["x"] * 22, segments=[13, 5, 4])
        self.assertEqual(s.segment_sizes, [13, 5, 4])
        self.assertEqual(s.median_segment_length, 5)

    def test_median_segment_length_even(self) -> None:
        s = DialogueSample(dial_id=0, utterances=["x"] * 8, segments=[2, 2, 2, 2])
        # sizes = [2, 2, 2, 2] -> median = 2
        self.assertEqual(s.median_segment_length, 2)

    def test_median_segment_length_odd(self) -> None:
        s = DialogueSample(dial_id=0, utterances=["x"] * 10, segments=[2, 3, 5])
        # sizes = [2, 3, 5] -> median = 3
        self.assertEqual(s.median_segment_length, 3)

    def test_no_segments_returns_full_length(self) -> None:
        s = DialogueSample(dial_id=0, utterances=["x"] * 7)
        self.assertEqual(s.segment_sizes, [7])
        self.assertEqual(s.median_segment_length, 7)

    def test_validation_rejects_empty_utterances(self) -> None:
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            DialogueSample(dial_id=0, utterances=[])

    def test_validation_rejects_negative_dial_id(self) -> None:
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            DialogueSample(dial_id=-1, utterances=["a", "b"])


class EvalLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = EvalLoader(DATA_ROOT)

    def test_load_all_6_corpora(self) -> None:
        for corpus in Corpus:
            with self.subTest(corpus=corpus):
                result = self.loader.load(corpus)
                self.assertIsInstance(result, LoadResult)
                self.assertGreater(result.total, 0)
                for sample in result.samples:
                    self.assertIsInstance(sample, DialogueSample)

    def test_meeting_committee_count(self) -> None:
        result = self.loader.load(Corpus.MEETING_COMMITTEE)
        self.assertEqual(result.total, 36)
        self.assertGreater(result.test_count, 0)
        first = result.samples[0]
        self.assertEqual(first.utterance_count, 370)
        self.assertEqual(first.segment_count, 8)
        # The first committee dialogue has 8 segments of sizes summing to 370
        self.assertEqual(sum(first.segment_sizes), 370)
        self.assertEqual(first.segment_sizes, [13, 32, 33, 16, 27, 130, 118, 1])

    def test_dialseg_711_count(self) -> None:
        result = self.loader.load(Corpus.DIALSEG_711)
        self.assertEqual(result.total, 711)

    def test_doc2dial_count(self) -> None:
        result = self.loader.load(Corpus.DOC2DIAL)
        self.assertEqual(result.total, 3270)

    def test_load_committee_under_100ms(self) -> None:
        import time
        t0 = time.perf_counter()
        self.loader.load(Corpus.MEETING_COMMITTEE)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 1.0, f"committee load took {elapsed:.3f}s; expected < 1.0s")

    def test_metadata_attached(self) -> None:
        result = self.loader.load(Corpus.MEETING_AMI)
        self.assertEqual(result.metadata.corpus, Corpus.MEETING_AMI)
        self.assertEqual(result.metadata.domain, "meeting")

    def test_missing_root_raises(self) -> None:
        with self.assertRaises(DataLoaderError):
            EvalLoader(Path("/nonexistent/path/that/does/not/exist"))


class DataLoaderErrorTests(unittest.TestCase):
    def test_malformed_json_raises(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "dialseg_711.json").write_text("{not valid json")
            loader = EvalLoader(tmp_path)
            with self.assertRaises(DataLoaderError):
                loader.load(Corpus.DIALSEG_711)

    def test_non_array_json_raises(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "dialseg_711.json").write_text('{"foo": "bar"}')
            loader = EvalLoader(tmp_path)
            with self.assertRaises(DataLoaderError):
                loader.load(Corpus.DIALSEG_711)

    def test_invalid_sample_raises(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Negative dial_id fails Pydantic validation
            (tmp_path / "dialseg_711.json").write_text('[{"dial_id": -1, "utterances": ["a", "b"], "segments": [2]}]')
            loader = EvalLoader(tmp_path)
            with self.assertRaises(DataLoaderError):
                loader.load(Corpus.DIALSEG_711)
