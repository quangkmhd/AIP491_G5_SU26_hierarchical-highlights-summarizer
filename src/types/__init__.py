"""Types layer -- core data structures shared across all layers.

No dependencies on any other layer. Pure data definitions only.
"""

from ._base import BaseSchema
from .hierarchical_recap import HierarchicalRecap, MeetingStatus
from .highlight import Highlight, HighlightSource, HighlightType
from .schemas import (
    HighlightUpsertRequest,
    MeetingProcessResponse,
    TranscriptIngestionRequest,
)
from .segment import Chunk, SegmentResult
from .transcript import DialogueTranscript
from .utterance import Utterance

__all__ = [
    # Base
    "BaseSchema",
    # Domain types
    "Utterance",
    "DialogueTranscript",
    "Chunk",
    "SegmentResult",
    "Highlight",
    "HighlightType",
    "HighlightSource",
    "HierarchicalRecap",
    "MeetingStatus",
    # API request/response schemas
    "TranscriptIngestionRequest",
    "HighlightUpsertRequest",
    "MeetingProcessResponse",
]
