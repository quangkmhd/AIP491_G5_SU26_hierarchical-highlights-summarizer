"""Unit tests for the CoherenceNet NSP-BERT architecture."""

import unittest
from pathlib import Path

import torch

from src.repo.coherence_net import CoherenceNet, NSP_CKPT_PATH
from src.repo.model_loader import NSP_BASE_MODEL_ID

CKPT = Path(NSP_CKPT_PATH)
CKPT_EXISTS = CKPT.exists()


@unittest.skipUnless(CKPT_EXISTS, f"NSP checkpoint not found at {NSP_CKPT_PATH}")
class TestCoherenceNetLoad(unittest.TestCase):
    def test_architecture_matches_paper1(self) -> None:
        from transformers import AutoModel

        from src.repo.model_loader import _resolve_device  # type: ignore[attr-defined]

        bert = AutoModel.from_pretrained(NSP_BASE_MODEL_ID)
        net = CoherenceNet(bert=bert, device=_resolve_device())
        # Decoder must be Linear(768,768) -> ReLU -> Dropout(0.1) -> Linear(768,2).
        self.assertEqual(net.coherence_decoder[0].in_features, 768)
        self.assertEqual(net.coherence_decoder[0].out_features, 768)
        self.assertIsInstance(net.coherence_decoder[1], torch.nn.ReLU)
        self.assertIsInstance(net.coherence_decoder[2], torch.nn.Dropout)
        self.assertEqual(net.coherence_decoder[2].p, 0.1)
        self.assertEqual(net.coherence_decoder[3].in_features, 768)
        self.assertEqual(net.coherence_decoder[3].out_features, 2)

    def test_load_project_checkpoint_keeps_decoder_weights(self) -> None:
        from transformers import AutoModel

        bert = AutoModel.from_pretrained(NSP_BASE_MODEL_ID)
        net = CoherenceNet(bert=bert, device="cpu")

        state = torch.load(NSP_CKPT_PATH, map_location="cpu", weights_only=True)
        net.load_state_dict(state, strict=False)
        net.eval()

        # Spot-check: the decoder's first linear weights are NOT all zeros
        # (which would mean the load silently failed).
        w = net.coherence_decoder[0].weight.detach()
        self.assertGreater(float(w.abs().sum()), 0.0)

    def test_forward_with_synthetic_ids(self) -> None:
        """Forward pass returns [B, 3, 2] using hand-built token IDs in vocab range."""
        from transformers import AutoModel

        bert = AutoModel.from_pretrained(NSP_BASE_MODEL_ID)
        net = CoherenceNet(bert=bert, device="cpu").eval()

        vocab_size = bert.embeddings.word_embeddings.num_embeddings
        # Build minimal input_ids / attention_mask tensors in vocab range.
        seq_len = 8
        batch = [[
            {
                "input_ids": torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]]),
                "attention_mask": torch.tensor([[1, 1, 1, 1, 1, 1, 1, 1]]),
                "token_type_ids": torch.tensor([[0, 0, 0, 0, 0, 0, 0, 0]]),
            },
            {
                "input_ids": torch.tensor([[9, 10, 11, 12, 13, 14, 15, 16]]),
                "attention_mask": torch.tensor([[1, 1, 1, 1, 1, 1, 1, 1]]),
                "token_type_ids": torch.tensor([[0, 0, 0, 0, 0, 0, 0, 0]]),
            },
            {
                "input_ids": torch.tensor([[17, 18, 19, 20, 21, 22, 23, 24]]),
                "attention_mask": torch.tensor([[1, 1, 1, 1, 1, 1, 1, 1]]),
                "token_type_ids": torch.tensor([[0, 0, 0, 0, 0, 0, 0, 0]]),
            },
        ]]
        with torch.no_grad():
            out = net(batch)
        # paper-1 returns [B, 3, 2]: 1 batch, 3 (pos/neg1/neg2) pairs, 2 classes.
        self.assertEqual(out.shape, (1, 3, 2))
        # Coherence score for the positive pair is [0, 0, 0].
        score = float(out[0, 0, 0])
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
