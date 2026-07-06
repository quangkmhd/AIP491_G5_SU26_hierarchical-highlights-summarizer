"""TextTilingService -- paper-1 TextTiling with depth-score cutoffs.

Ported from references_code/dialogue-topic-segmenter/neural_texttiling.py:
    - depth_computing(scores) -> np.ndarray
    - boundaries_to_segments(indices, total) -> list[int]
    - threshold = mean + alpha * std  (paper §3, alpha tuned on dev set)

The TextTilingService consumes a score list from CoherenceScorer and emits
SegmentEvent for each detected boundary.

Paper reference (neural_texttiling.py:157-178):
    similarity_scores = similarity_computing(dialogue, tokenizer, text_encoder, mode, device)
    depth_scores = depth_computing(similarity_scores)
    threshold = depth_scores.mean() + alpha * depth_scores.std()
    boundaries = [i for i in range(len(depth_scores)) if depth_scores[i] > threshold] + [len(dialogue)-1]
    segments = boundaries_to_segments(boundaries, len(dialogue))

Customization for streaming (not in paper):
    - process() is a pure-ish function: state is reset at the start of
      each call so the same TextTilingService instance can be reused
      across multiple dialogues.
    - The last boundary (len(dialogue)-1) is always appended as a
      force-close event so the tail segment is emitted. The paper does
      this in the boundary list directly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.config.text_tiling import TextTilingConfig
from src.logging import get_logger


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


def cutoff_threshold(depths: np.ndarray, alpha: float = 0.0) -> float:
    """Compute the boundary cutoff threshold tau.

    Paper formula (neural_texttiling.py:166):
        threshold = depth_scores.mean() + alpha * depth_scores.std()

    Alpha is tuned on a dev set in the paper (range [-2, 2], step 0.1).
    Default alpha=0 means threshold = mean.
    """
    mu = float(np.mean(depths))
    sigma = float(np.std(depths))
    return mu + alpha * sigma


def boundaries_to_segments(
    boundary_indices: list[int], total_entries: int
) -> list[int]:
    """Convert boundary indices to segment sizes (paper convention).

    Ported from neural_texttiling.py::boundaries_to_segment_sizes.
    boundary_indices are the indices AT WHICH a segment ends (inclusive).
    The caller must include total_entries-1 as the last boundary.
    """
    segment_sizes: list[int] = []
    previous_boundary = -1
    for boundary in boundary_indices:
        segment_sizes.append(boundary - previous_boundary)
        previous_boundary = boundary
    return segment_sizes


class TextTilingService:
    """TextTiling on a coherence-score list.

    Consumes a list of (n-1) coherence scores from CoherenceScorer and
    emits SegmentEvent for each detected boundary.
    """

    def __init__(self, config: TextTilingConfig | None = None) -> None:
        self.logger = get_logger("src.service.text_tiling")
        self.config = config or TextTilingConfig()
        self._segment_counter = 0

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

        State is reset at the start of each call so the same instance can
        be reused across multiple dialogues.
        """
        # Reset state — makes process() safe to call multiple times.
        self._segment_counter = 0
        current_start = 0

        if n_utterances < 2:
            return []
        if len(scores) != n_utterances - 1:
            raise ValueError(
                f"scores length ({len(scores)}) must equal n_utterances - 1 "
                f"({n_utterances - 1})"
            )

        depths = depth_computing(scores)
        tau = cutoff_threshold(depths, alpha=self.config.alpha)
        n_boundaries = int((depths > tau).sum())
        self.logger.info(
            "text_tiling scores=%d n_utterances=%d depths_min=%.4f depths_max=%.4f "
            "tau=%.4f alpha=%.2f boundaries=%d",
            len(scores), n_utterances,
            float(depths.min()), float(depths.max()),
            tau, self.config.alpha, n_boundaries,
        )

        events: list[SegmentEvent] = []
        # Paper: boundaries = [i for i in range(len(depth_scores)) if depth_scores[i] > threshold]
        # boundary i means topic shift between utt i and utt i+1.
        # The closed segment ends at utt i (inclusive).
        for i, d in enumerate(depths):
            if d > tau:
                events.append(
                    SegmentEvent(
                        segment_id=self._new_segment_id(),
                        utterances_start=current_start,
                        utterances_end=i,
                        depth_score=float(d),
                        boundary_index=i,
                    )
                )
                current_start = i + 1

        # Paper: + [len(dialogue)-1]  — always close the tail segment.
        if current_start < n_utterances:
            events.append(
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=current_start,
                    utterances_end=n_utterances - 1,
                    depth_score=0.0,
                    boundary_index=n_utterances - 1,
                )
            )
        elif not events:
            # Edge case: n_utterances >= 2 but no boundaries and no tail
            # (shouldn't happen since current_start=0 < n-1 when n>=2).
            events.append(
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=0,
                    utterances_end=n_utterances - 1,
                    depth_score=0.0,
                    boundary_index=n_utterances - 1,
                )
            )
        return events
