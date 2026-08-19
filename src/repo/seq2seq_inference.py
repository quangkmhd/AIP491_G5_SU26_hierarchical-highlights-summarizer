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
    """Encode input text and generate output text using a Seq2Seq Transformer model."""
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
            max_length=None,
            no_repeat_ngram_size=3,
            length_penalty=1.0,
            early_stopping=True,
            do_sample=False,
        )
    return handle.tokenizer.batch_decode(token_ids, skip_special_tokens=True)[0].strip()


class ViT5ChunkSummarizer:
    """ViT5 model used for summarizing dialogue chunks (up to 8 utterances/chunk)."""
    def __init__(self, handle: ModelHandle) -> None:
        self.handle = handle

    def summarize(self, text: str) -> str:
        """Summarize a dialogue chunk using the ViT5 model."""
        return generate_seq2seq_text(
            self.handle,
            text,
            prefix="Tóm tắt: ",
            max_input_tokens=512,
            max_new_tokens=128,
        )


class BARTphoTopicTitler:
    """BARTpho model used for generating chapter titles for topic segments."""
    def __init__(self, handle: ModelHandle) -> None:
        self.handle = handle

    def generate_title(self, text: str) -> str:
        """Generate a chapter title using the BARTpho model."""
        return generate_seq2seq_text(
            self.handle,
            text,
            prefix="Tạo tiêu đề: ",
            max_input_tokens=1024,
            max_new_tokens=200,
        )
