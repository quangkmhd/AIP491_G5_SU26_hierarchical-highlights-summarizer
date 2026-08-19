from __future__ import annotations

import torch

from .model_loader import ModelHandle


def generate_seq2seq_text(
    handle: ModelHandle,
    text: str,
    prefix: str = "",
    max_input_tokens: int = 512,
    max_new_tokens: int = 128,
) -> str:
    """Mã hóa văn bản đầu vào và sinh văn bản đầu ra bằng mô hình Transformer Seq2Seq."""
    encoded = handle.tokenizer(
        prefix + text,
        max_length=max_input_tokens,
        truncation=True,
        return_tensors="pt",
    ).to(handle.device)

    with torch.inference_mode():
        token_ids = handle.model.generate(
            **encoded,
            num_beams=4,
            max_new_tokens=max_new_tokens,
            no_repeat_ngram_size=3,
            length_penalty=1.0,
            early_stopping=True,
            do_sample=False,
        )

    return handle.tokenizer.batch_decode(token_ids, skip_special_tokens=True)[0].strip()


class ViT5ChunkSummarizer:
    """Mô hình ViT5 dùng để tóm tắt các khối câu thoại (tối đa 8 câu/khối)."""

    def __init__(self, handle: ModelHandle) -> None:
        self.handle = handle

    def summarize(self, text: str) -> str:
        """Tóm tắt khối thoại bằng mô hình ViT5."""
        return generate_seq2seq_text(
            self.handle,
            text,
            prefix="Tóm tắt: ",
            max_input_tokens=512,
            max_new_tokens=128,
        )


class BARTphoTopicTitler:
    """Mô hình BARTpho dùng để sinh tiêu đề cho các phân đoạn chương chủ đề."""

    def __init__(self, handle: ModelHandle) -> None:
        self.handle = handle

    def generate_title(self, text: str) -> str:
        """Sinh tiêu đề chương bằng mô hình BARTpho."""
        return generate_seq2seq_text(
            self.handle,
            text,
            prefix="Tạo tiêu đề: ",
            max_input_tokens=1024,
            max_new_tokens=200,
        )
