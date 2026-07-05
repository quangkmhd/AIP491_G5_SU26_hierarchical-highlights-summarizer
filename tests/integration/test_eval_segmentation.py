"""Integration test for eval-001: runs the segmentation metrics harness
on a small synthetic DialogueSample with known ground truth.

This test verifies the metric computation pipeline end-to-end without
loading the heavy NSP-BERT model.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.data import Corpus, DialogueSample, EvalLoader
from src.eval.segmentation_metrics import f1_score, pk, win_diff


def _ends_from_sizes(sizes: list[int]) -> list[int]:
    """Convert segment SIZES to end indices (1 past last utt in segment)."""
    ends = []
    cursor = 0
    for s in sizes:
        cursor += s
        ends.append(cursor - 1)
    return ends


class SegmentationMetricsOnDataTests(unittest.TestCase):
    def test_perfect_match_on_committee_first_sample(self) -> None:
        # Ground truth for committee sample 0: 8 segments summing to 370 utt
        gt_sizes = [13, 32, 33, 16, 27, 130, 118, 1]
        gt_ends = _ends_from_sizes(gt_sizes)
        # Same prediction = perfect score
        self.assertEqual(pk(gt_ends, gt_ends), 0.0)
        self.assertEqual(win_diff(gt_ends, gt_ends), 0.0)
        self.assertEqual(f1_score(gt_ends, gt_ends), 1.0)

    def test_perfect_against_eval_loader_sample(self) -> None:
        loader = EvalLoader(ROOT / "data" / "eval_vi")
        result = loader.load(Corpus.MEETING_COMMITTEE)
        sample = result.samples[0]
        gt_ends = _ends_from_sizes(sample.segment_sizes)
        # Self-match
        self.assertEqual(f1_score(gt_ends, gt_ends), 1.0)
        self.assertEqual(pk(gt_ends, gt_ends), 0.0)

    def test_perturbation_degrades_score(self) -> None:
        loader = EvalLoader(ROOT / "data" / "eval_vi")
        result = loader.load(Corpus.MEETING_COMMITTEE)
        sample = result.samples[0]
        gt_ends = _ends_from_sizes(sample.segment_sizes)
        # Shift every end by +5 -> F1 should drop
        perturbed = [e + 5 for e in gt_ends if e + 5 < sample.utterance_count - 1]
        if len(perturbed) > 0:
            f1_perturbed = f1_score(perturbed, gt_ends)
            self.assertLess(f1_perturbed, 1.0)

    def test_corpus_loads_for_all_6_corpora(self) -> None:
        # Verify data-001 EvalLoader still works (eval-001 depends on it)
        loader = EvalLoader(ROOT / "data" / "eval_vi")
        for corpus in Corpus:
            result = loader.load(corpus)
            self.assertGreater(result.total, 0)
            for sample in result.samples[:1]:
                ends = _ends_from_sizes(sample.segment_sizes)
                self.assertEqual(pk(ends, ends), 0.0)
