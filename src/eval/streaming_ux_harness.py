"""Streaming UX Evaluation Harness (eval-002).

Per spec D3: with DR1 dropped, the harness evaluates streaming UX quality
of the Hierarchical recap only (no "highlights vs hierarchical" comparison).

Captures per-participant ratings (synthetic by default) for 4 metrics:
  1. Time-to-first-chapter (seconds, from SSE connection open to first
     segment-closed event received in browser)
  2. Comfort with skeleton state (1-5 Likert)
  3. Discoverability of Copy + Show-Context (1-5 Likert)
  4. Overall streaming UX score (1-5 Likert)

Output: a markdown report at docs/generated/streaming-ux-report.md.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable


@dataclass
class ParticipantRatings:
    """Per-participant UX measurements for the streaming recap."""

    participant_id: int
    time_to_first_chapter_s: float
    comfort_with_skeleton: int = 0
    discoverability: int = 0
    overall_ux: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        for name, value in [
            ("comfort_with_skeleton", self.comfort_with_skeleton),
            ("discoverability", self.discoverability),
            ("overall_ux", self.overall_ux),
        ]:
            if not 1 <= value <= 5:
                raise ValueError(f"{name} must be in [1, 5]; got {value}")


def _synthetic_participant(participant_id: int) -> ParticipantRatings:
    """Return a synthetic participant's ratings (for the harness structural test)."""
    return ParticipantRatings(
        participant_id=participant_id,
        time_to_first_chapter_s=2.5 + 0.5 * participant_id,  # 2.5s, 3.0s, ...
        comfort_with_skeleton=4,
        discoverability=4,
        overall_ux=4,
        notes=f"Synthetic participant {participant_id}",
    )


def collect_ratings(
    n_participants: int = 7,
    rater: Callable[[int], ParticipantRatings] = _synthetic_participant,
) -> list[ParticipantRatings]:
    """Collect ratings from `rater(participant_id)` for participants 1..N."""
    return [rater(pid) for pid in range(1, n_participants + 1)]


def aggregate(ratings: list[ParticipantRatings]) -> dict:
    return {
        "n_participants": len(ratings),
        "mean_time_to_first_chapter_s": mean(r.time_to_first_chapter_s for r in ratings),
        "mean_comfort_with_skeleton": mean(r.comfort_with_skeleton for r in ratings),
        "mean_discoverability": mean(r.discoverability for r in ratings),
        "mean_overall_ux": mean(r.overall_ux for r in ratings),
    }


def render_markdown(ratings: list[ParticipantRatings], agg: dict) -> str:
    lines = [
        "# Streaming UX Report",
        "",
        f"**Participants:** {agg['n_participants']}",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Mean |",
        "|--------|------|",
        f"| Time-to-first-chapter (s) | {agg['mean_time_to_first_chapter_s']:.2f} |",
        f"| Comfort with skeleton (1-5) | {agg['mean_comfort_with_skeleton']:.2f} |",
        f"| Discoverability of Copy + Show-Context (1-5) | {agg['mean_discoverability']:.2f} |",
        f"| Overall streaming UX (1-5) | {agg['mean_overall_ux']:.2f} |",
        "",
        "## Per-Participant Data",
        "",
        "| ID | Time to 1st Chapter (s) | Skeleton Comfort | Discoverability | Overall UX | Notes |",
        "|----|------------------------|------------------|-----------------|------------|-------|",
    ]
    for r in ratings:
        lines.append(
            f"| {r.participant_id} | {r.time_to_first_chapter_s:.2f} | {r.comfort_with_skeleton} | "
            f"{r.discoverability} | {r.overall_ux} | {r.notes} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="src.eval.streaming_ux_harness")
    parser.add_argument("--participants", "-n", type=int, default=7, help="N participants (default 7)")
    parser.add_argument("--output", "-o", type=Path, default=Path("docs/generated/streaming-ux-report.md"))
    args = parser.parse_args(argv)

    ratings = collect_ratings(args.participants)
    agg = aggregate(ratings)
    report = render_markdown(ratings, agg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
