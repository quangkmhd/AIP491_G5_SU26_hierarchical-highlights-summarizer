"""Unit tests for TextTilingService + depth_computing (paper-1 §3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.config.text_tiling import TextTilingConfig
from src.service.text_tiling import (
    SegmentEvent,
    TextTilingService,
    boundaries_to_segments,
    cutoff_threshold,
    depth_computing,
)


class DepthComputingTests(unittest.TestCase):
    def test_constant_scores_yield_zero_depth(self) -> None:
        scores = [0.5] * 5
        depths = depth_computing(scores)
        # All depths should be 0 (no peak/trough)
        np.testing.assert_array_almost_equal(depths, [0.0] * 5)

    def test_valley_in_middle_yields_high_depth(self) -> None:
        # scores: [1, 1, 0.0, 1, 1] -> depth at i=2 is the valley
        scores = [1.0, 1.0, 0.0, 1.0, 1.0]
        depths = depth_computing(scores)
        # depth[2] = 0.5 * (1 + 1 - 0) = 1.0
        self.assertAlmostEqual(depths[2], 1.0, places=5)
        # Other depths are 0
        for i in [0, 1, 3, 4]:
            self.assertAlmostEqual(depths[i], 0.0, places=5)

    def test_endpoint_depth(self) -> None:
        # scores: [0.0, 1, 1, 1]. depth[0] = 0.5 * (0 + 1 - 0) = 0.5
        # depth[1] = 0.5 * (0 + 1 - 2*1) = -0.5
        # depth[3] = 0.5 * (1 + 1 - 2*1) = 0
        scores = [0.0, 1.0, 1.0, 1.0]
        depths = depth_computing(scores)
        self.assertAlmostEqual(depths[0], 0.5, places=5)
        self.assertAlmostEqual(depths[3], 0.0, places=5)


class CutoffThresholdTests(unittest.TestCase):
    def test_alpha_zero_returns_mean(self) -> None:
        # Paper: threshold = mean + alpha * std. alpha=0 -> threshold = mean.
        depths = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
        mu = float(np.mean(depths))
        self.assertAlmostEqual(cutoff_threshold(depths, alpha=0.0), mu, places=5)

    def test_alpha_positive_raises_threshold(self) -> None:
        depths = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
        mu = float(np.mean(depths))
        sigma = float(np.std(depths))
        expected = mu + 0.5 * sigma
        self.assertAlmostEqual(cutoff_threshold(depths, alpha=0.5), expected, places=5)

    def test_alpha_negative_lowers_threshold(self) -> None:
        depths = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
        mu = float(np.mean(depths))
        sigma = float(np.std(depths))
        expected = mu + (-1.0) * sigma
        self.assertAlmostEqual(cutoff_threshold(depths, alpha=-1.0), expected, places=5)


class BoundariesToSegmentsTests(unittest.TestCase):
    def test_empty_boundaries_returns_empty(self) -> None:
        # Paper: no boundaries -> no segments (caller must append len-1).
        self.assertEqual(boundaries_to_segments([], 10), [])

    def test_two_boundaries_three_segments(self) -> None:
        # boundaries at 3 and 7 on a 10-utterance dialogue -> sizes 4, 4
        # (paper: caller appends len-1=9 as last boundary for 3 segments)
        result = boundaries_to_segments([3, 7], 10)
        self.assertEqual(result, [4, 4])

    def test_with_last_boundary(self) -> None:
        # boundaries at 3, 7, 9 (9 = len-1) -> sizes 4, 4, 2
        result = boundaries_to_segments([3, 7, 9], 10)
        self.assertEqual(result, [4, 4, 2])


class TextTilingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = TextTilingConfig()
        self.service = TextTilingService(self.config)

    def test_default_config_window_30_stride_10(self) -> None:
        self.assertEqual(self.config.window_size, 30)
        self.assertEqual(self.config.stride, 10)
        self.assertEqual(self.config.alpha, 1.0)

    def test_short_input_returns_no_events(self) -> None:
        events = self.service.process([0.5], n_utterances=2)
        # 2 utterances: 1 score. The service should not crash; may emit
        # a force-close event for the tail.
        self.assertGreaterEqual(len(events), 1)
        # Last event covers all 2 utterances
        last = events[-1]
        self.assertEqual(last.utterances_start, 0)
        self.assertEqual(last.utterances_end, 1)

    def test_length_mismatch_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.service.process([0.1, 0.2, 0.3], n_utterances=10)

    def test_no_topical_shifts_yields_single_segment(self) -> None:
        # All scores equal -> depths all 0 -> tau = mean = 0 -> no boundary
        # crossed except force-close
        scores = [0.5] * 9
        events = self.service.process(scores, n_utterances=10)
        # Only the force-close event
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].utterances_start, 0)
        self.assertEqual(events[0].utterances_end, 9)

    def test_synthetic_3_topic_shifts(self) -> None:
        # Build scores with 3 clear valleys. Pattern: 3 highs, 1 valley, 2 highs,
        # 1 valley, 2 highs, 1 valley, 2 highs. Total scores = 3+1+2+1+2+1+2 = 12,
        # total utterances = 13.
        scores = [0.9] * 3 + [0.1] + [0.9] * 2 + [0.1] + [0.9] * 2 + [0.1] + [0.9] * 2
        self.assertEqual(len(scores), 12)
        events = self.service.process(scores, n_utterances=13)
        # Filter for actual boundary events (skip force-close if any)
        boundaries = [e for e in events if e.depth_score > 0.0]
        # Each valley should be detected as a boundary
        self.assertGreaterEqual(len(boundaries), 3)

    def test_segment_ids_unique(self) -> None:
        scores = [0.9] * 3 + [0.1] + [0.9] * 2 + [0.1] + [0.9] * 2 + [0.1] + [0.9] * 2
        events = self.service.process(scores, n_utterances=13)
        ids = [e.segment_id for e in events]
        self.assertEqual(len(ids), len(set(ids)))

    def test_segments_non_overlapping(self) -> None:
        scores = [0.9, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9, 0.9]
        events = self.service.process(scores, n_utterances=9)
        # Each segment's start should equal the previous end + 1
        for i in range(1, len(events)):
            self.assertEqual(
                events[i].utterances_start,
                events[i - 1].utterances_end + 1,
            )

    def test_full_coverage(self) -> None:
        scores = [0.9, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9, 0.9]
        # 8 scores -> 9 utterances
        events = self.service.process(scores, n_utterances=9)
        # First event starts at 0
        self.assertEqual(events[0].utterances_start, 0)
        # Last event ends at n_utterances - 1
        self.assertEqual(events[-1].utterances_end, 8)

    def test_process_reset_state_on_reuse(self) -> None:
        """Bug #1: calling process() twice on the same instance must reset state."""
        scores1 = [0.9, 0.9, 0.1, 0.9, 0.9]
        events1 = self.service.process(scores1, n_utterances=6)
        # Second call should start fresh from utterance 0
        scores2 = [0.9, 0.9, 0.1, 0.9, 0.9]
        events2 = self.service.process(scores2, n_utterances=6)
        # First event of second call must start at 0, not carry over state
        self.assertEqual(events2[0].utterances_start, 0)
        # Segment IDs should restart from seg-0
        self.assertEqual(events2[0].segment_id, "seg-0")
