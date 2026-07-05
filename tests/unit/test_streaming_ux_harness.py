"""Unit tests for the streaming UX evaluation harness (eval-002)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eval.streaming_ux_harness import (
    ParticipantRatings,
    _synthetic_participant,
    aggregate,
    collect_ratings,
    render_markdown,
)


class StreamingUxHarnessTests(unittest.TestCase):
    def test_collect_default_7_participants(self) -> None:
        ratings = collect_ratings()
        self.assertEqual(len(ratings), 7)

    def test_aggregate_computes_means(self) -> None:
        ratings = [
            ParticipantRatings(1, 2.0, 4, 4, 4),
            ParticipantRatings(2, 4.0, 5, 5, 5),
        ]
        agg = aggregate(ratings)
        self.assertEqual(agg["n_participants"], 2)
        self.assertAlmostEqual(agg["mean_time_to_first_chapter_s"], 3.0)
        self.assertAlmostEqual(agg["mean_overall_ux"], 4.5)

    def test_render_markdown_has_required_columns(self) -> None:
        ratings = [_synthetic_participant(i) for i in range(1, 4)]
        agg = aggregate(ratings)
        md = render_markdown(ratings, agg)
        # Must contain the 4 metric labels
        self.assertIn("Time-to-first-chapter", md)
        self.assertIn("Comfort with skeleton", md)
        self.assertIn("Discoverability", md)
        self.assertIn("Overall streaming UX", md)
        # Must NOT mention highlights (DR1 dropped)
        self.assertNotIn("highlights", md.lower())
        # Must have a per-participant table row for each participant
        for r in ratings:
            self.assertIn(f"| {r.participant_id} |", md)

    def test_report_excludes_highlights_column(self) -> None:
        # Spec D3: report has no 'highlights' column
        ratings = collect_ratings(3)
        agg = aggregate(ratings)
        md = render_markdown(ratings, agg)
        # The aggregate header should not have "highlights"
        aggregate_section = md.split("## Per-Participant")[0]
        self.assertNotIn("highlights", aggregate_section.lower())

    def test_synthetic_participant_ratings_in_range(self) -> None:
        for pid in range(1, 8):
            p = _synthetic_participant(pid)
            self.assertGreaterEqual(p.comfort_with_skeleton, 1)
            self.assertLessEqual(p.comfort_with_skeleton, 5)
            self.assertGreaterEqual(p.discoverability, 1)
            self.assertLessEqual(p.discoverability, 5)
            self.assertGreaterEqual(p.overall_ux, 1)
            self.assertLessEqual(p.overall_ux, 5)
