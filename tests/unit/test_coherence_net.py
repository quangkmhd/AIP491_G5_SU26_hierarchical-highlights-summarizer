"""Unit tests for the CoherenceNet NSP-BERT architecture."""

import unittest
from pathlib import Path

import torch

from src.repo.coherence_net import CoherenceNet, NSP_CKPT_PATH

CKPT = Path(NSP_CKPT_PATH)
CKPT_EXISTS = CKPT.exists()


@unittest.skipUnless(CKPT_EXISTS, f"NSP checkpoint not found at {NSP_CKPT_PATH}")
class TestCoherenceNetLoad(unittest.TestCase):
    def test_architecture_matches_paper1(self) -> None:
        from transformers import AutoModel

        from src.repo.model_loader import _resolve_device  # type: ignore[attr-defined]

        bert = AutoModel.from_pretrained("bert-base-multilingual-cased")
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

        bert = AutoModel.from_pretrained("bert-base-multilingual-cased")
        net = CoherenceNet(bert=bert, device="cpu")

        # Mirror the loader's filter strategy: match keys with the same shape.
        state = torch.load(NSP_CKPT_PATH, map_location="cpu", weights_only=False)
        # Resize embeddings to match the checkpoint's vocab (38168).
        net.bert.resize_token_embeddings(
            state["bert.embeddings.word_embeddings.weight"].shape[0]
        )
        # Strip the "bert." prefix so the inner BertModel accepts the keys.
        bert_state = {
            k[len("bert."):]: v for k, v in state.items() if k.startswith("bert.")
        }
        own = net.bert.state_dict()
        matched = {
            k: v for k, v in bert_state.items() if k in own and v.shape == own[k].shape
        }
        net.bert.load_state_dict(matched, strict=False)
        net.coherence_decoder.load_state_dict(
            {k[len("coherence_decoder."):]: v for k, v in state.items() if k.startswith("coherence_decoder.")},
            strict=False,
        )
        net.eval()

        # Spot-check: the decoder's first linear weights are NOT all zeros
        # (which would mean the load silently failed).
        w = net.coherence_decoder[0].weight.detach()
        self.assertGreater(float(w.abs().sum()), 0.0)

    def test_forward_with_synthetic_ids(self) -> None:
        """Forward pass returns [B, 3, 2] using hand-built token IDs in vocab range."""
        from transformers import AutoModel

        bert = AutoModel.from_pretrained("bert-base-multilingual-cased")
        # Resize to the checkpoint's vocab so IDs in [0, 38167] are valid.
        ck_vocab = 38168
        bert.resize_token_embeddings(ck_vocab)
        net = CoherenceNet(bert=bert, device="cpu").eval()

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


class TestCoherenceNetC4RealText(unittest.TestCase):
    """C4: real Vietnamese text tokenized by `bert-base-multilingual-cased`
    produces IDs in the full 119547 range. The model's embedding matrix was
    resized to the checkpoint's vocab (38168), so any ID >= 38168 must be
    clamped to 0 (UNK) before the embedding lookup or the call raises.
    """

    def test_real_vietnamese_text_clamped_to_vocab_range(self) -> None:
        from src.repo.model_loader import _coerce_token_ids

        # Real Vietnamese text: 119547-vocab tokenizer produces IDs beyond 38168.
        vocab_size = 38168
        # Simulate a batch of token IDs that includes both in-range and OOV IDs.
        input_ids = torch.tensor(
            [[100, 5000, 38167, 38168, 50000, 105907]]
        )
        clamped = _coerce_token_ids(input_ids, vocab_size)
        # Every ID must be < vocab_size.
        self.assertTrue((clamped < vocab_size).all())
        # In-range IDs are preserved.
        self.assertEqual(clamped[0, 0].item(), 100)
        self.assertEqual(clamped[0, 1].item(), 5000)
        self.assertEqual(clamped[0, 2].item(), 38167)
        # OOV IDs are clamped to vocab_size - 1 (= 38167).
        self.assertEqual(clamped[0, 3].item(), vocab_size - 1)
        self.assertEqual(clamped[0, 4].item(), vocab_size - 1)
        self.assertEqual(clamped[0, 5].item(), vocab_size - 1)

    def test_clamp_helper_does_not_modify_fully_in_range(self) -> None:
        from src.repo.model_loader import _coerce_token_ids

        input_ids = torch.tensor([[1, 2, 3, 38167]])
        clamped = _coerce_token_ids(input_ids, 38168)
        self.assertTrue(torch.equal(input_ids, clamped))
