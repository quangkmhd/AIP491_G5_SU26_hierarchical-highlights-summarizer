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
from .demo_timeline import Custom10hTimeline, DemoTimelineItem, PlaybackPause
from .hierarchical_summarization import HierarchicalSummarizationService
from .meeting_recap_orchestrator import (
    OrchestratorEvent,
    RecapEventType,
    StreamingOrchestrator,
)
from .sliding_text_tiling import SegmentEvent, SlidingTextTilingService

__all__ = [
    "AsrEngine",
    "ChunkingService",
    "Custom10hTimeline",
    "DemoTimelineItem",
    "HierarchicalSummarizationService",
    "OrchestratorEvent",
    "PlaybackPause",
    "RecapEventType",
    "SegmentEvent",
    "SlidingTextTilingService",
    "StreamingOrchestrator",
]
