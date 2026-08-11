"""Types layer -- core data structures shared across all layers.

No dependencies on any other layer. Pure data definitions only.
"""

from ._base import BaseSchema
from .audio import (
    AppliedAudioSettings,
    AudioQualityMetrics,
    AudioSessionStart,
    FinalUtteranceEvent,
)
from .hierarchical_recap import HierarchicalRecap, MeetingStatus
# Highlight family removed in model-001+ (DR1 dropped from scope).
from .schemas import (
    MeetingProcessResponse,
    TranscriptIngestionRequest,
)
from .segment import Chunk, SegmentResult
from .transcript import DialogueTranscript
from .utterance import Utterance

__all__ = [
    # Base
    "BaseSchema",
    "AppliedAudioSettings",
    "AudioQualityMetrics",
    "AudioSessionStart",
    "FinalUtteranceEvent",
    # Domain types
    "Utterance",
    "DialogueTranscript",
    "Chunk",
    "SegmentResult",
    "HierarchicalRecap",
    "MeetingStatus",
    # API request/response schemas
    "TranscriptIngestionRequest",
    "MeetingProcessResponse",
]
