"""Service layer -- pure-logic services: scoring, segmentation, summarization, orchestration.

Independent of runtime/ui. May depend on types/config/repo.
"""

from .chunking_service import ChunkingService
from .coherence_scorer import CoherenceScorer
from .hierarchical_summarization import HierarchicalSummarizationService
from .meeting_recap_orchestrator import (
    OrchestratorEvent,
    RecapEventType,
    StreamingOrchestrator,
)
from .text_tiling import SegmentEvent, TextTilingService

__all__ = [
    "ChunkingService",
    "CoherenceScorer",
    "HierarchicalSummarizationService",
    "OrchestratorEvent",
    "RecapEventType",
    "SegmentEvent",
    "StreamingOrchestrator",
    "TextTilingService",
]
