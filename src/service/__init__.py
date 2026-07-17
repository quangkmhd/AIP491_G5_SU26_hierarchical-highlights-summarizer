"""Service layer -- pure-logic services: segmentation, summarization, orchestration.

Independent of runtime/ui. May depend on types/config/repo.

The current pipeline uses lexical Sliding TextTiling (BoW + cosine
+ multi-scale depth) for topic segmentation; the NSP-BERT CoherenceScorer
was removed along with this rewrite.
"""

try:
    from .asr_engine import AsrEngine
except ImportError:
    AsrEngine = None  # type: ignore[assignment,misc]
from .chunking_service import ChunkingService
from .hierarchical_summarization import HierarchicalSummarizationService
from .meeting_recap_orchestrator import (
    OrchestratorEvent,
    RecapEventType,
    StreamingOrchestrator,
)
from .text_tiling import SegmentEvent, SlidingTextTilingService

__all__ = [
    "AsrEngine",
    "ChunkingService",
    "HierarchicalSummarizationService",
    "OrchestratorEvent",
    "RecapEventType",
    "SegmentEvent",
    "SlidingTextTilingService",
    "StreamingOrchestrator",
]