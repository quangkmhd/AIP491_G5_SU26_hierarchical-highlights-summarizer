"""Domain interfaces for ASR model drivers."""

from abc import ABC, abstractmethod
from typing import Tuple
import numpy as np
from .entities import TranscriptionResult


class ASRModelInterface(ABC):
    @abstractmethod
    def transcribe_waveform(
        self, samples: np.ndarray, sample_rate: int, filename: str = None
    ) -> TranscriptionResult:
        """Transcribe an audio waveform array (float32, 16kHz mono)."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if model is loaded and ready for inference."""
        pass
