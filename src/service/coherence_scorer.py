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
        # Load the CoherenceNet handle once at construction; this caches the
        # per-process singleton.
        self.logger.info("loading CoherenceNet (mode CM)")
        self._handle = self._loader.load_coherence_net()
        self._model: CoherenceNet = self._handle.model
        self._tokenizer = self._handle.tokenizer
        self._device = self._handle.device
        # Embedding vocab size for token-id clamping (C4 mitigation)
        self._vocab_size: int = self._model.bert.embeddings.word_embeddings.num_embeddings
        self.logger.info("CoherenceNet loaded vocab_size=%d device=%s", self._vocab_size, self._device)

    def _clamp_input_ids(self, input_ids: torch.Tensor) -> torch.Tensor:
        """Clamp out-of-range token IDs to 0 (UNK) to avoid embedding lookup errors.

        See model-002 _coerce_token_ids for the full rationale. Logs
        a debug-level message when clamping occurs so operators can see
        how often the C4 mitigation fires.
        """
        n_clamped = int((input_ids >= self._vocab_size).sum().item())
        if n_clamped > 0:
            self.logger.debug("clamped %d out-of-range token ids to UNK", n_clamped)
        return torch.where(
            input_ids >= self._vocab_size,
            torch.zeros_like(input_ids),
            input_ids,
        )

    def score_pair(self, utt_i: str, utt_i_plus_1: str) -> float:
        """Score a single pair. Returns a float in [0, 1]."""
        tokenized = self._tokenizer(
            utt_i,
            utt_i_plus_1,
            padding=_PADDING,
            max_length=_MAX_LENGTH,
            truncation=True,
            return_tensors="pt",
        )
        # C4 mitigation: clamp out-of-range token IDs to UNK (0) before
        # passing to BERT, so the embedding lookup doesn't raise.
        tokenized["input_ids"] = self._clamp_input_ids(tokenized["input_ids"])

        # Paper reference: forward call wraps the pair in [pos, neg1, neg2] structure
        # but we only need the positive pair for inference; reuse the same
        # tokenization 3x to match the [B, 3, 2] output shape.
        sample = [tokenized, tokenized, tokenized]
        with torch.no_grad():
            output = self._model([sample])
        # output shape: [1, 3, 2]; positive pair is sample 0; coherence prob is class 0
        return float(output[0, 0, 0].item())

    def score_stream(self, utterances: list[str]) -> Iterator[float]:
        """Score all consecutive pairs in a list. Yields n-1 floats."""
        for i in range(len(utterances) - 1):
            yield self.score_pair(utterances[i], utterances[i + 1])
