"""TextTilingService -- paper-1 sliding-window TextTiling with depth-score cutoffs.

Ported from references_code/dialogue-topic-segmenter/neural_texttiling.py:
    - depth_computing(scores) -> list[float]
    - boundaries_to_segments(indices, total) -> list[int]
    - depth_score cutoff: tau = mu - sigma/2

The TextTilingService consumes a score stream from CoherenceScorer and emits
SegmentEvent as depth-score cutoffs are crossed. Sliding-window params
(window=30, stride=10) come from TextTilingConfig (config-001+).

This is the *Ours (full)* method from paper-1 Table 4 (the best-performing
method in the paper). See docs/superpowers/specs/2026-07-05-streaming-
hierarchical-recap-design.md D4 for details.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.config.text_tiling import TextTilingConfig


@dataclass(frozen=True)
class SegmentEvent:
    """A single segment-closed event emitted by TextTilingService.

    The `boundary_index` is the index of the LAST utterance in the closed
    segment (inclusive). The `depth_score` is the value that crossed tau.
    """

    segment_id: str
    utterances_start: int
    utterances_end: int
    depth_score: float
    boundary_index: int


def depth_computing(scores: list[float]) -> np.ndarray:
    """Port of neural_texttiling.py::depth_computing.

    For each score s[i], search left and right to find the highest peak
    on each side (hl, hr), then depth = 0.5 * (hl + hr - 2 * s[i]).
    """
    n = len(scores)
    out = np.zeros(n, dtype=float)
    for i in range(n):
        left_flag = scores[i]
        right_flag = scores[i]
        # Search left
        for j in range(i - 1, -1, -1):
            if scores[j] >= left_flag:
                left_flag = scores[j]
            else:
                break
        # Search right
        for j in range(i + 1, n):
            if scores[j] >= right_flag:
                right_flag = scores[j]
            else:
                break
        out[i] = 0.5 * (left_flag + right_flag - 2 * scores[i])
    return out


def cutoff_threshold(depths: np.ndarray, policy: str = "mean-std/2") -> float:
    """Compute the boundary cutoff threshold tau.

    paper-1 §3 specifies tau = mu - sigma/2 ("mean-std/2" policy).
    """
    mu = float(np.mean(depths))
    if policy == "mean-std/2":
        sigma = float(np.std(depths))
        return mu - sigma / 2.0
    if policy == "mean":
        return mu
    if policy == "mean+std":
        return mu + float(np.std(depths))
    raise ValueError(f"Unknown cutoff policy: {policy!r}")


def boundaries_to_segments(
    boundary_indices: list[int], total_entries: int
) -> list[int]:
    """Convert boundary indices to segment sizes (paper convention).

    boundary_indices are the indices AT WHICH a segment ends (inclusive).
    The last entry of the dialogue is always a boundary.
    """
    if not boundary_indices:
        return [total_entries]
    sizes: list[int] = []
    prev = -1
    for b in boundary_indices:
        sizes.append(b - prev)
        prev = b
    # The last boundary should be total_entries - 1
    if boundary_indices[-1] != total_entries - 1:
        sizes.append(total_entries - 1 - prev)
    return sizes


class TextTilingService:
    """Sliding-window TextTiling on a coherence-score stream.

    Consumes a list of (n-1) coherence scores from CoherenceScorer.score_stream
    and emits SegmentEvent when the depth score crosses the cutoff threshold.
    """

    def __init__(self, config: TextTilingConfig | None = None) -> None:
        self.config = config or TextTilingConfig()
        self._segment_counter = 0
        self._current_start = 0

    def _new_segment_id(self) -> str:
        sid = f"seg-{self._segment_counter}"
        self._segment_counter += 1
        return sid

    def process(
        self, scores: list[float], n_utterances: int
    ) -> list[SegmentEvent]:
        """Run TextTiling on a list of n-1 coherence scores.

        Returns a list of SegmentEvent, one per detected boundary. The list
        always ends with a "force-close" event at the end of the dialogue
        so the last segment is emitted.
        """
        if n_utterances < 2:
            return []
        if len(scores) != n_utterances - 1:
            raise ValueError(
                f"scores length ({len(scores)}) must equal n_utterances - 1 "
                f"({n_utterances - 1})"
            )

        depths = depth_computing(scores)
        tau = cutoff_threshold(depths, policy="mean-std/2")

        events: list[SegmentEvent] = []
        # boundary i means the i-th pair's first utterance starts a new
        # segment; equivalently, the segment [0..i] is closed.
        # Paper convention: pair i is between utt i and utt i+1. A high
        # depth at i means topic shift between utt i and utt i+1.
        # The closed segment ends at utt i (inclusive).
        for i, d in enumerate(depths):
            if d > tau:
                events.append(
                    SegmentEvent(
                        segment_id=self._new_segment_id(),
                        utterances_start=self._current_start,
                        utterances_end=i,
                        depth_score=float(d),
                        boundary_index=i,
                    )
                )
                self._current_start = i + 1
        # Force-close any remaining tail
        if self._current_start < n_utterances - 1:
            events.append(
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=self._current_start,
                    utterances_end=n_utterances - 1,
                    depth_score=0.0,
                    boundary_index=n_utterances - 1,
                )
            )
            self._current_start = n_utterances
        return events
