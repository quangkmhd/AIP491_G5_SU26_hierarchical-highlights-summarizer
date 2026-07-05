"""Service layer -- pure-logic services: scoring, segmentation, summarization, orchestration.

Independent of runtime/ui. May depend on types/config/repo.
"""

from .coherence_scorer import CoherenceScorer
from .text_tiling import SegmentEvent, TextTilingService

__all__ = [
    "CoherenceScorer",
    "SegmentEvent",
    "TextTilingService",
]
