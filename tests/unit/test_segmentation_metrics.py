"""Unit tests for P_k, Win-Diff, and F1 metrics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eval.segmentation_metrics import f1_score, pk, win_diff


class PkTests(unittest.TestCase):
    def test_perfect_prediction(self) -> None:
        # Predict [13, 18, 22] on 23 utterances, true is also [13, 18, 22]
        self.assertEqual(pk([13, 18, 22], [13, 18, 22]), 0.0)

    def test_off_by_one(self) -> None:
        # Predict [14, 19, 22] vs true [13, 18, 22]. With small window=2 the
        # mismatch should produce some P_k > 0.
        score = pk([14, 19, 22], [13, 18, 22], window=2)
        self.assertGreater(score, 0.0)

    def test_completely_wrong(self) -> None:
        # No boundaries in common
        score = pk([5, 10, 15], [3, 8, 13], window=2)
        self.assertGreater(score, 0.0)


class WinDiffTests(unittest.TestCase):
    def test_perfect(self) -> None:
        self.assertEqual(win_diff([13, 18, 22], [13, 18, 22]), 0.0)

    def test_off_by_one(self) -> None:
        # Predict [12, 20, 22] vs true [13, 18, 22] -> WD > 0
        score = win_diff([12, 20, 22], [13, 18, 22], window=2)
        self.assertGreater(score, 0.0)

    def test_windiff_differs_from_pk(self) -> None:
        # A case where the number of boundaries in window differs but endpoints agree or vice-versa
        # Let true segment ends be [2, 5, 8] (total length 9)
        # Let predicted segment ends be [2, 8] (missing boundary at 5)
        true_ends = [2, 5, 8]
        pred_ends = [2, 8]
        pk_score = pk(pred_ends, true_ends, window=3)
        wd_score = win_diff(pred_ends, true_ends, window=3)
        self.assertNotEqual(pk_score, wd_score)


class F1Tests(unittest.TestCase):
    def test_perfect(self) -> None:
        self.assertAlmostEqual(f1_score([13, 18, 22], [13, 18, 22]), 1.0, places=5)

    def test_no_overlap(self) -> None:
        # No matching segment boundaries
        score = f1_score([5, 10, 15], [3, 8, 13])
        self.assertLess(score, 0.5)

    def test_empty(self) -> None:
        self.assertEqual(f1_score([], [1, 2]), 0.0)
        self.assertEqual(f1_score([1, 2], []), 0.0)
