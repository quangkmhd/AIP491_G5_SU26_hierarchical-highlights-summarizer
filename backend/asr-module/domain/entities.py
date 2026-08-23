"""Domain entities for ASR service."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioSegment:
    samples: list  # float32 values [-1.0, 1.0]
    sample_rate: int
    duration_seconds: float
    filename: Optional[str] = None


@dataclass
class TranscriptionResult:
    text: str
    duration_seconds: float
    sample_rate: int
    filename: Optional[str] = None
    processing_time_ms: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    status: str = "success"
