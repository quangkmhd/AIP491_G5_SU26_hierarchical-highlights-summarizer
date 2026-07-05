"""CoherenceNet -- paper-1 NSP-BERT coherence scorer.

Architecture (verified against `vibert_checkpoints_vi/cpt_4000.pth`,
see docs/superpowers/specs/2026-07-04-model-002-design.md D1):

    bert: BertModel (bert-base-multilingual-cased, vocab 38168 subset)
    coherence_decoder: Sequential(
        Linear(768, 768),
        ReLU(),
        Dropout(p=0.1),
        Linear(768, 2),
    )

Forward signature mirrors the paper-1 reference implementation
(`references_code/dialogue-topic-segmenter/model_utils.py`):
input is a list of `[pos_pair, neg1_pair, neg2_pair]` triples where
each pair is a dict of tokenized tensors (input_ids, attention_mask,
token_type_ids). The network returns a tensor of softmax probabilities
per sample with shape `[B, 3, 2]`. The coherence score for the
positive pair of the i-th sample is `output[i, 0, 0]`.

This is a cross-encoder (NSP) by design; paper-1 Section 3.2 chose
this over a bi-encoder because cross-encoders outperform bi-encoders
for pairwise scoring (Thakur et al., 2021).
"""

from __future__ import annotations

from pathlib import Path
from typing import NewType

import torch
from torch import nn

# CoherenceScore is a unit-less float in [0, 1]; declared as a NewType
# for static type-checking only (it is a plain float at runtime).
CoherenceScore = NewType("CoherenceScore", float)

# Path to the project's pre-trained NSP checkpoint.
# The file is git-ignored (see .gitignore) but ships in the local clone.
NSP_CKPT_PATH: str = "vibert_checkpoints_vi/cpt_4000.pth"


class CoherenceNet(nn.Module):
    """NSP-BERT coherence scoring module (paper-1 Section 3.2)."""

    def __init__(self, bert: nn.Module, device: str) -> None:
        super().__init__()
        self.bert = bert
        self.coherence_decoder = nn.Sequential(
            nn.Linear(768, 768),
            nn.ReLU(),
            nn.Dropout(p=0.1),
            nn.Linear(768, 2),
        )
        self.device = device

    def forward(self, batch: list[list[dict]]) -> torch.Tensor:
        """Score a batch of (pos, neg1, neg2) utterance-pair triples.

        Returns a tensor of shape `[B, 3, 2]` containing softmax
        probabilities. The coherence score for the positive pair of
        the first sample is `output[0, 0, 0]`.
        """
        outputs: list[torch.Tensor] = []
        for sample in batch:
            cls_per_head: list[torch.Tensor] = []
            for pair in sample:
                # Move each tensor in the pair dict to the right device.
                moved = {k: v.to(self.device) for k, v in pair.items()}
                encoded = self.bert(**moved)
                # CLS hidden state: [1, 768] -> squeeze to [768].
                cls = encoded.last_hidden_state[:, 0, :].squeeze(0)
                decoded = self.coherence_decoder(cls)  # [2]
                cls_per_head.append(torch.softmax(decoded, dim=-1))  # [2]
            outputs.append(torch.stack(cls_per_head, dim=0))  # [3, 2]
        return torch.stack(outputs, dim=0)  # [B, 3, 2]

    def coerce_checkpoint_path(self, path: str | Path) -> Path:
        """Validate that a checkpoint path exists; raise a clear error otherwise."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(
                f"NSP checkpoint not found at {p}. "
                f"Expected the pre-trained cpt_*.pth file at the project root."
            )
        return p
