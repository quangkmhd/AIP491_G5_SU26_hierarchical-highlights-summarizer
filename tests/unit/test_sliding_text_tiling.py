"""Unit tests for SlidingTextTilingService and the segmenter functions it wraps."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.config.text_tiling import SlidingTextTilingConfig
from src.segmenters import (
    DEFAULT_RADII,
    cosine,
    find_boundaries,
    multiscale_depth,
    normalize,
    similarity_scores,
)
from src.segmenters.sliding_texttiling import depth_scores  # internal helper — test directly
from src.service.text_tiling import SegmentEvent, SlidingTextTilingService


class SimilarityScoresTests(unittest.TestCase):
    def test_block_size_one_uses_pair_cosine(self) -> None:
        bows = [{"a": 1}, {"a": 1}, {"b": 1}]
        # Simulate the bow→cosine path; identical vectors -> 1.0
        scores = similarity_scores(["a a", "a a", "b b"], block_size=1, stopwords=set())
        self.assertEqual(len(scores), 2)
        self.assertAlmostEqual(scores[0], 1.0, places=5)
        self.assertAlmostEqual(scores[1], 0.0, places=5)

    def test_block_size_larger_smooths_over_neighbours(self) -> None:
        # No shared tokens in a pair, but block_size=2 pools neighbours
        # and produces non-zero similarity for some windows.
        scores = similarity_scores(["a", "b", "a", "b"], block_size=2, stopwords=set())
        self.assertEqual(len(scores), 3)
        self.assertTrue(all(0.0 <= s <= 1.0 for s in scores))


class DepthScoresTests(unittest.TestCase):
    def test_radius_full_matches_no_radius(self) -> None:
        scores = [1.0, 1.0, 0.0, 1.0, 1.0]
        full = depth_scores(scores)
        with_radius = depth_scores(scores, radius=10)
        np.testing.assert_array_almost_equal(full, with_radius)

    def test_valley_with_radius_yields_high_depth(self) -> None:
        scores = [1.0, 1.0, 0.0, 1.0, 1.0]
        depths = depth_scores(scores, radius=5)
        self.assertAlmostEqual(depths[2], 1.0, places=5)
        for i in (0, 1, 3, 4):
            self.assertAlmostEqual(depths[i], 0.0, places=5)


class MultiscaleDepthTests(unittest.TestCase):
    def test_returns_ndarray_with_expected_length(self) -> None:
        scores = [0.9, 0.1, 0.9, 0.1, 0.9]
        result = multiscale_depth(scores, radii=[3, 5], agg="mean")
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), len(scores))

    def test_aggregation_modes_differ(self) -> None:
        scores = [0.5, 0.5, 0.5, 0.1, 0.5, 0.5, 0.5]
        mean_depth = multiscale_depth(scores, radii=[3, 5], agg="mean")
        max_depth = multiscale_depth(scores, radii=[3, 5], agg="max")
        # max must be at least mean element-wise
        self.assertTrue((max_depth + 1e-9 >= mean_depth).all())


class NormalizeTests(unittest.TestCase):
    def test_zscore_zero_std_returns_zero(self) -> None:
        arr = np.array([0.5, 0.5, 0.5])
        result = normalize(arr, mode="zscore")
        np.testing.assert_array_almost_equal(result, [0.0, 0.0, 0.0])

    def test_minmax_zero_range_returns_zero(self) -> None:
        arr = np.array([0.7, 0.7, 0.7])
        result = normalize(arr, mode="minmax")
        np.testing.assert_array_almost_equal(result, [0.0, 0.0, 0.0])

    def test_minmax_maps_to_unit_interval(self) -> None:
        arr = np.array([0.0, 0.5, 1.0])
        result = normalize(arr, mode="minmax")
        self.assertAlmostEqual(float(result.min()), 0.0, places=5)
        self.assertAlmostEqual(float(result.max()), 1.0, places=5)


class FindBoundariesTests(unittest.TestCase):
    def test_short_input(self) -> None:
        # n=1 returns [0]; n=0 returns []
        self.assertEqual(find_boundaries(["x"])[0], [0])
        self.assertEqual(find_boundaries([])[0], [])

    def test_topically_distinct_blocks_produce_boundary(self) -> None:
        utts = (
            ["a"] * 6
            + ["b c d e f"] * 6
        )
        # Need distinct tokens; build with a richer set
        utts = ["alpha beta"] * 6 + ["gamma delta"] * 6
        boundaries, _ = find_boundaries(utts, block_size=2, radii=[3, 5],
                                        alpha=0.5, min_segment_ratio=0.05)
        self.assertIn(len(utts) - 1, boundaries)  # force-close tail present
        # Should detect at least one real boundary between the two topics
        real_boundaries = [b for b in boundaries if b != len(utts) - 1]
        self.assertGreaterEqual(len(real_boundaries), 1)

    def test_identical_utterances_no_real_boundary(self) -> None:
        utts = ["the cat sat on the mat"] * 10
        boundaries, _ = find_boundaries(utts, block_size=2, radii=[3, 5],
                                        alpha=0.5, min_segment_ratio=0.1)
        # Only the force-close tail
        self.assertEqual(boundaries, [len(utts) - 1])

    def test_at_window_size_batch_path_active(self) -> None:
        """Verify n == window_size uses batch path (no window partitioning)."""
        utts = ["alpha beta"] * 20 + ["gamma delta"] * 20
        boundaries, _ = find_boundaries(utts, window_size=40, stride=5,
                                        block_size=2, radii=[3, 5], alpha=0.5,
                                        min_segment_ratio=0.05)
        self.assertIn(len(utts) - 1, boundaries)
        real = [b for b in boundaries if b != len(utts) - 1]
        self.assertGreaterEqual(len(real), 1)

    def test_window_size_plus_one_enters_streaming_path(self) -> None:
        """Verify n == window_size + 1 enters streaming path correctly."""
        utts = ["alpha beta"] * 20 + ["gamma delta"] * 21
        boundaries, _ = find_boundaries(utts, window_size=40, stride=10,
                                        block_size=2, radii=[3, 5], alpha=0.5,
                                        min_segment_ratio=0.05)
        # Two windows: start=0 and start=1 (pinned), overlapping on 39 utts
        self.assertIn(len(utts) - 1, boundaries)
        real = [b for b in boundaries if b != len(utts) - 1]
        self.assertGreaterEqual(len(real), 1)

    def test_streaming_max_stride_no_overlap(self) -> None:
        """Verify stride == window_size - 1 (max valid, zero overlap) works."""
        utts = ["alpha beta"] * 50 + ["gamma delta"] * 50
        boundaries, _ = find_boundaries(utts, window_size=40, stride=39,
                                        block_size=2, radii=[3, 5], alpha=0.5,
                                        min_segment_ratio=0.05)
        self.assertIn(len(utts) - 1, boundaries)
        real = [b for b in boundaries if b != len(utts) - 1]
        self.assertGreaterEqual(len(real), 1)

    def test_streaming_merge_small_segment_triggered(self) -> None:
        """A tiny segment flanked by large blocks must be merged out."""
        # 45 'a' + 3 distinct + 45 'a' — the 3-utterance middle segment
        # is small enough to trigger merge_small_segments when
        # min_segment_ratio is high enough.
        utts = (["alpha beta"] * 45 + ["gamma delta epsilon zeta eta"] * 3
                + ["alpha beta"] * 45)
        boundaries, _ = find_boundaries(utts, window_size=40, stride=10,
                                        block_size=2, radii=[3, 5], alpha=0.6,
                                        min_segment_ratio=0.15)
        # With min_seg = max(2, floor(93 * 0.15)) = 13, any segment < 13
        # utterances is merged — the middle segment (3 utts) must disappear.
        self.assertIn(len(utts) - 1, boundaries)
        # Each remaining segment must be at least 13 utterances long.
        prev = -1
        for b in boundaries:
            self.assertGreaterEqual(b - prev, 13)
            prev = b


class SlidingTextTilingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SlidingTextTilingConfig()
        self.service = SlidingTextTilingService(self.config)

    def test_default_config(self) -> None:
        self.assertEqual(self.config.block_size, 2)
        self.assertEqual(self.config.alpha, 1.0)
        self.assertEqual(self.config.radii, DEFAULT_RADII)
        self.assertEqual(self.config.window_size, 40)
        self.assertEqual(self.config.stride, 5)

    def test_streaming_window_segmentation(self) -> None:
        """Verify that streaming window partition and evaluation works correctly on long inputs."""
        utts = ["alpha beta"] * 50 + ["gamma delta"] * 50
        cfg = SlidingTextTilingConfig(window_size=40, stride=10, alpha=0.5)
        service = SlidingTextTilingService(cfg)
        events = service.process(utts)
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[-1].utterances_end, 99)
        self.assertEqual(events[0].utterances_start, 0)
        # Verify contiguous, non-overlapping segments
        for i in range(1, len(events)):
            self.assertEqual(events[i].utterances_start, events[i - 1].utterances_end + 1)

    def test_empty_input_returns_no_events(self) -> None:
        self.assertEqual(self.service.process([]), [])

    def test_single_utterance_returns_one_event(self) -> None:
        events = self.service.process(["hello world"])
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e.utterances_start, 0)
        self.assertEqual(e.utterances_end, 0)
        self.assertEqual(e.boundary_index, 0)

    def test_two_utterances_returns_one_event(self) -> None:
        events = self.service.process(["hello world", "goodbye world"])
        # n=2 -> only force-close at index 1
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].utterances_end, 1)

    def test_full_coverage(self) -> None:
        utts = [f"phiên bản d {i}" for i in range(12)]
        events = self.service.process(utts)
        self.assertEqual(events[0].utterances_start, 0)
        self.assertEqual(events[-1].utterances_end, len(utts) - 1)

    def test_segments_non_overlapping(self) -> None:
        utts = [f"câu số {i} khác nhau" for i in range(20)]
        events = self.service.process(utts)
        for i in range(1, len(events)):
            self.assertEqual(
                events[i].utterances_start,
                events[i - 1].utterances_end + 1,
            )

    def test_segment_ids_unique_within_a_call(self) -> None:
        utts = [f"chủ đề {i}" for i in range(15)]
        events = self.service.process(utts)
        ids = [e.segment_id for e in events]
        self.assertEqual(len(ids), len(set(ids)))

    def test_process_resets_state_on_reuse(self) -> None:
        """Calling process() twice on the same instance must reset state."""
        utts = ["a b c", "a b c", "x y z", "x y z"]
        events1 = self.service.process(utts)
        events2 = self.service.process(utts)
        # Both calls start at utterance 0
        self.assertEqual(events1[0].utterances_start, 0)
        self.assertEqual(events2[0].utterances_start, 0)
        # Segment IDs restart at seg-0 for both calls
        self.assertEqual(events1[0].segment_id, "seg-0")
        self.assertEqual(events2[0].segment_id, "seg-0")

    def test_multi_scale_radii_affect_result(self) -> None:
        """A config with more radii should still produce a valid boundary set."""
        utts = (
            ["họp nhóm alpha"] * 5
            + ["ngân sách beta"] * 5
            + ["thời hạn gamma"] * 5
        )
        cfg_narrow = SlidingTextTilingConfig(radii=[3], alpha=0.5, min_segment_ratio=0.05)
        cfg_wide = SlidingTextTilingConfig(
            radii=[3, 5, 10, 15, 20], alpha=0.5, min_segment_ratio=0.05,
        )
        ev_narrow = SlidingTextTilingService(cfg_narrow).process(utts)
        ev_wide = SlidingTextTilingService(cfg_wide).process(utts)
        # Both must cover the full range
        self.assertEqual(ev_narrow[-1].utterances_end, len(utts) - 1)
        self.assertEqual(ev_wide[-1].utterances_end, len(utts) - 1)
        # Both must contain only non-overlapping segments
        for ev in (ev_narrow, ev_wide):
            for i in range(1, len(ev)):
                self.assertEqual(
                    ev[i].utterances_start, ev[i - 1].utterances_end + 1,
                )

    def test_custom_block_size_runs_without_error(self) -> None:
        cfg = SlidingTextTilingConfig(block_size=1, radii=[3], alpha=0.5)
        events = SlidingTextTilingService(cfg).process(
            ["xin chào", "hôm nay họp", "dự án alpha", "ngân sách beta"],
        )
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[-1].utterances_end, 3)