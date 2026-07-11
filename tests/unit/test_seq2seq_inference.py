import unittest

import torch

from src.repo.model_loader import ModelHandle, ModelKind
from src.repo.seq2seq_inference import (
    BARTphoTopicTitler, GenerationError, ViT5ChunkSummarizer,
)


class Batch(dict):
    def to(self, device):
        self.device = device
        return self


class TokenizerDouble:
    def __init__(self, output="  kết quả  "):
        self.output = output
        self.inputs = None
        self.kwargs = None
        self.decode_kwargs = None

    def __call__(self, inputs, **kwargs):
        self.inputs, self.kwargs = inputs, kwargs
        return Batch(input_ids=torch.tensor([[1]]))

    def batch_decode(self, ids, **kwargs):
        self.decode_kwargs = kwargs
        return [self.output]


class ModelDouble:
    def __init__(self):
        self.generate_kwargs = None
        self.inference_mode = False

    def generate(self, **kwargs):
        self.inference_mode = not torch.is_grad_enabled()
        self.generate_kwargs = {k: v for k, v in kwargs.items() if k != "input_ids"}
        return torch.tensor([[2]])


class OOMModel(ModelDouble):
    def generate(self, **kwargs):
        raise torch.cuda.OutOfMemoryError("allocation failed")


def handle(kind, output="  kết quả  "):
    return ModelHandle(kind, ModelDouble(), TokenizerDouble(output), "cuda", "/model")


class Seq2SeqAdapterTests(unittest.TestCase):
    def test_vit5_contract(self):
        h = handle(ModelKind.CHUNK_SUMMARIZER)
        self.assertEqual(ViT5ChunkSummarizer(h).summarize("S1: Nội dung"), "kết quả")
        self.assertEqual(h.tokenizer.inputs, "Tóm tắt: S1: Nội dung")
        self.assertEqual(h.tokenizer.kwargs["max_length"], 512)
        self.assertEqual(h.model.generate_kwargs["max_new_tokens"], 128)
        self.assertEqual(h.model.generate_kwargs["num_beams"], 4)
        self.assertTrue(h.model.inference_mode)
        self.assertEqual(h.tokenizer.decode_kwargs, {"skip_special_tokens": True})

    def test_bartpho_contract(self):
        h = handle(ModelKind.TOPIC_TITLER)
        BARTphoTopicTitler(h).generate_title("Một / Hai")
        self.assertEqual(h.tokenizer.inputs, "Tạo tiêu đề: Một / Hai")
        self.assertEqual(h.tokenizer.kwargs["max_length"], 1024)
        self.assertEqual(h.model.generate_kwargs["max_new_tokens"], 200)
        self.assertEqual(h.model.generate_kwargs["no_repeat_ngram_size"], 3)
        self.assertEqual(h.model.generate_kwargs["length_penalty"], 1.0)
        self.assertTrue(h.model.generate_kwargs["early_stopping"])
        self.assertFalse(h.model.generate_kwargs["do_sample"])

    def test_empty_output_is_actionable(self):
        h = handle(ModelKind.TOPIC_TITLER, "  ")
        with self.assertRaisesRegex(GenerationError, r"topic_titler.*fix"):
            BARTphoTopicTitler(h).generate_title("Một")

    def test_adapter_rejects_wrong_handle_kind(self):
        with self.assertRaises(ValueError):
            ViT5ChunkSummarizer(handle(ModelKind.TOPIC_TITLER))

    def test_cuda_oom_is_actionable_and_chained(self):
        h = ModelHandle(
            ModelKind.CHUNK_SUMMARIZER,
            OOMModel(),
            TokenizerDouble(),
            "cuda",
            "/model",
        )
        with self.assertRaisesRegex(GenerationError, r"VRAM.*fix") as raised:
            ViT5ChunkSummarizer(h).summarize("S1: Nội dung")
        self.assertIsInstance(raised.exception.__cause__, torch.cuda.OutOfMemoryError)


if __name__ == "__main__":
    unittest.main()
