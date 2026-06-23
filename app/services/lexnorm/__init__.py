"""Lexical normalization pre-stage for tool 09.

Public re-exports:

    Utterance, CorrectionResult       -- data shapes
    TranscriptCorrector               -- per-utterance corrector
    TranscriptNormalizer              -- whole-transcript orchestrator
    ModelUnavailableError             -- raised when the corrector model is not on the Ollama server
"""

from app.services.lexnorm.types_ import CorrectionResult, Utterance
from app.services.lexnorm.corrector import (
    ModelUnavailableError,
    TranscriptCorrector,
    TranscriptNormalizer,
)

__all__ = [
    "CorrectionResult",
    "ModelUnavailableError",
    "TranscriptCorrector",
    "TranscriptNormalizer",
    "Utterance",
]
