from __future__ import annotations

from typing import Any

import numpy as np


class SherpaSpeakerEmbedder:
    """Adapt sherpa-onnx SpeakerEmbeddingExtractor to extract speaker embeddings."""

    def __init__(self, extractor: Any, sample_rate: int = 16000) -> None:
        self.extractor = extractor
        self.sample_rate = sample_rate

    def extract(self, samples: np.ndarray) -> np.ndarray:
        stream = self.extractor.create_stream()
        stream.accept_waveform(self.sample_rate, samples)
        stream.input_finished()
        return np.asarray(self.extractor.compute(stream), dtype=np.float32).reshape(-1)


__all__ = ["SherpaSpeakerEmbedder"]
