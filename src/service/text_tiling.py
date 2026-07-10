"""SlidingTextTilingService -- multi-scale Sliding TextTiling.

Pipeline (per-process call):
  1. BoW every utterance (Vietnamese stop-word filtered by default).
  2. Cosine similarity at every consecutive gap, pooling each side
     into a `block_size` window.
  3. Depth scores at multiple peak-search radii (one per `radii[i]`).
  4. Per-radius z-score normalization; aggregate (mean/max/sum) into a
     single multi-scale depth profile.
  5. Threshold: mean + alpha * std.
  6. Post-process: merge any segment smaller than `min_segment_ratio`
     to its shallower-depth neighbour.
  7. Emit a SegmentEvent for every boundary; force-close the tail
     segment with a final event at the last utterance index.

The service consumes utterance strings directly and computes its own
similarity — no external scoring model is required. The SegmentEvent
shape matches the historical paper-1 service so downstream consumers
(orchestrator, recap types) do not need to be re-shaped.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config.text_tiling import SlidingTextTilingConfig
from src.logging import get_logger
from src.segmenters import find_boundaries


@dataclass(frozen=True)
class SegmentEvent:
    """A single segment-closed event emitted by SlidingTextTilingService.

    The `boundary_index` is the index of the LAST utterance in the
    closed segment (inclusive). The `depth_score` is the (aggregated)
    depth at that boundary; the force-close tail event uses 0.0.
    """

    segment_id: str
    utterances_start: int
    utterances_end: int
    depth_score: float
    boundary_index: int


class SlidingTextTilingService:
    """Multi-scale Sliding TextTiling on raw utterance text.

    Stateless across calls: each `process()` invocation produces a fresh
    segment-id sequence starting from `seg-0`, so the same service
    instance can be reused across many dialogues.
    """

    def __init__(self, config: SlidingTextTilingConfig | None = None) -> None:
        self.logger = get_logger("src.service.text_tiling")
        self.config = config or SlidingTextTilingConfig()
        self._segment_counter = 0
        if self.config.use_stopwords:
            import stopwordsiso
            self._stopwords = stopwordsiso.stopwords(["vi"])
        else:
            self._stopwords = set()

    def _new_segment_id(self) -> str:
        sid = f"seg-{self._segment_counter}"
        self._segment_counter += 1
        return sid

    def process(self, utterances: list[str]) -> list[SegmentEvent]:
        """Detect topic boundaries on a list of utterance strings.

        Returns a list of SegmentEvent covering the full utterance range
        in non-overlapping segments. The last event is always a
        force-close at the final utterance index.
        """
        # Reset per-call state so this service instance is reusable.
        self._segment_counter = 0

        n = len(utterances)
        if n == 0:
            return []
        if n == 1:
            return [
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=0,
                    utterances_end=0,
                    depth_score=0.0,
                    boundary_index=0,
                )
            ]

        boundaries, boundary_depths = find_boundaries(
            utterances,
            block_size=self.config.block_size,
            radii=self.config.radii,
            alpha=self.config.alpha,
            stopwords=self._stopwords,
            agg=self.config.agg,
            normalize_mode=self.config.normalize,
            min_segment_ratio=self.config.min_segment_ratio,
        )

        # find_boundaries guarantees boundaries[-1] == n - 1; assert to
        # surface drift if the segmenter contract ever changes.
        assert boundaries and boundaries[-1] == n - 1, (
            "find_boundaries must append n-1 as the force-close tail"
        )

        # Count real (non-tail) boundaries for logging clarity.
        n_boundaries = sum(1 for b in boundaries if b != n - 1)
        self.logger.info(
            "sliding_text_tiling n_utterances=%d n_boundaries=%d alpha=%.2f radii=%s "
            "block_size=%d agg=%s normalize=%s",
            n, n_boundaries, self.config.alpha, self.config.radii,
            self.config.block_size, self.config.agg, self.config.normalize,
        )

        events: list[SegmentEvent] = []
        prev = -1
        for b in boundaries:
            is_tail = b == n - 1
            depth = 0.0 if is_tail else float(boundary_depths.get(b, 0.0))
            events.append(
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=prev + 1,
                    utterances_end=b,
                    depth_score=depth,
                    boundary_index=b,
                )
            )
            prev = b
        return events