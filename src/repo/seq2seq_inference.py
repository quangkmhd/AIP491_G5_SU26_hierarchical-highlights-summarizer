from __future__ import annotations

import torch

from .model_loader import ModelHandle


class _Seq2SeqGenerator:
    prefix: str
    max_input_tokens: int
    max_new_tokens: int

    def __init__(self, handle: ModelHandle) -> None:
        """Khởi tạo generator Seq2Seq với mô hình và tokenizer tương ứng."""
        self._model = handle.model
        self._tokenizer = handle.tokenizer
        self._device = handle.device

    def _generate(self, body: str, task_name: str) -> str:
        """Thực hiện quá trình mã hóa input và sinh văn bản đầu ra bằng mô hình seq2seq."""
        try:
            encoded = self._tokenizer(
                self.prefix + body,
                max_length=self.max_input_tokens,
                truncation=True,
                return_tensors="pt",
            ).to(self._device)
            with torch.inference_mode():
                token_ids = self._model.generate(
                    **encoded,
                    num_beams=4,
                    max_new_tokens=self.max_new_tokens,
                    no_repeat_ngram_size=3,
                    length_penalty=1.0,
                    early_stopping=True,
                    do_sample=False,
                )
        except torch.cuda.OutOfMemoryError as exc:
            raise RuntimeError(f"{task_name} exhausted CUDA VRAM") from exc
        output = self._tokenizer.batch_decode(token_ids, skip_special_tokens=True)[0].strip()
        if not output:
            raise RuntimeError(f"{task_name} returned empty output")
        return output


class ViT5ChunkSummarizer(_Seq2SeqGenerator):
    prefix = "Tóm tắt: "
    max_input_tokens = 512
    max_new_tokens = 128

    def summarize(self, formatted_utterances: str) -> str:
        """Tóm tắt khối thoại bằng mô hình ViT5."""
        return self._generate(formatted_utterances, "chunk_summarizer")


class BARTphoTopicTitler(_Seq2SeqGenerator):
    prefix = "Tạo tiêu đề: "
    max_input_tokens = 1024
    max_new_tokens = 200

    def generate_title(self, joined_summaries: str) -> str:
        """Sinh tiêu đề bằng mô hình BARTpho."""
        return self._generate(joined_summaries, "topic_titler")
