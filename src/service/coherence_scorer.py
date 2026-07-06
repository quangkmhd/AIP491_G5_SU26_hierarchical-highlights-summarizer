"""CoherenceScorer -- paper-1 NSP-BERT utterance-pair coherence scoring (mode CM).

Wraps `CoherenceNet` (from model-002) and exposes a streaming API for the
TextTiling service. This is mode "CM" (Coherence Modeling) in the paper
reference code (`references_code/dialogue-topic-segmenter/segment.py:79-81`),
which uses the fine-tuned coherence scoring model to score each pair.

The model takes a pair of utterances and returns a single float in [0, 1]
representing topical coherence (high = same topic, low = topic shift).
"""

from __future__ import annotations

from typing import Iterator

import torch

from src.logging import get_logger
from src.repo.coherence_net import CoherenceNet
from src.repo.model_loader import ModelLoader

# Matches the paper code at references_code/dialogue-topic-segmenter/neural_texttiling.py:35
_PADDING = "max_length"
_MAX_LENGTH = 128


class CoherenceScorer:
    """Stream-mode utterance-pair coherence scorer using the paper-1 CoherenceNet.

    The forward call uses the paper-1 mode CM: feed only the positive pair
    (not the negatives used during training). The coherence score is the
    softmax probability of class 0 (`output[0, 0, 0]`) of the [B, 3, 2] output.
    """

    def __init__(self, loader: ModelLoader | None = None) -> None:
        self.logger = get_logger("src.service.coherence_scorer")
        self._loader = loader or ModelLoader.instance()
        self.logger.info("loading CoherenceNet (mode CM)")
        self._handle = self._loader.load_coherence_net()
        self._model: CoherenceNet = self._handle.model
        self._tokenizer = self._handle.tokenizer
        self._device = self._handle.device
        self._total_pairs_scored: int = 0
        self.logger.info("CoherenceNet loaded device=%s", self._device)

    def score_pair(self, utt_i: str, utt_i_plus_1: str) -> float:
        """Score a single pair. Returns a float in [0, 1]."""
        self._total_pairs_scored += 1
        tokenized = self._tokenizer(
            utt_i,
            utt_i_plus_1,
            padding=_PADDING,
            max_length=_MAX_LENGTH,
            truncation=True,
            return_tensors="pt",
        )

        sample = [tokenized, tokenized, tokenized]
        with torch.no_grad():
            output = self._model([sample])
        return float(output[0, 0, 0].item())

    def score_stream(self, utterances: list[str]) -> Iterator[float]:
        """Score all consecutive pairs in a list. Yields n-1 floats."""
        n_pairs = len(utterances) - 1
        for i in range(n_pairs):
            yield self.score_pair(utterances[i], utterances[i + 1])
