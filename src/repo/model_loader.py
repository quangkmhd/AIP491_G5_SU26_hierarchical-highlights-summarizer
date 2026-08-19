from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VIT5_MODEL_PATH = PROJECT_ROOT / "models" / "vit5-chunk-summarizer-v1"
BARTPHO_MODEL_PATH = PROJECT_ROOT / "models" / "bartpho-topic-titler-v2" / "checkpoint-230"


class ModelHandle:
    """Đối tượng chứa thông tin mô hình PyTorch và Tokenizer đã được nạp."""

    def __init__(self, model: Any, tokenizer: Any, device: str) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.device = device


def load_seq2seq_model(path: Path) -> ModelHandle:
    """Nạp mô hình Transformer Seq2Seq và Tokenizer từ đường dẫn đĩa cục bộ."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True)
    model.to(device)
    model.eval()
    return ModelHandle(model=model, tokenizer=tokenizer, device=device)


class ModelLoader:
    """Quản lý nạp và lưu cache 2 mô hình ViT5 và BARTpho."""

    def __init__(self) -> None:
        self._vit5_handle: ModelHandle | None = None
        self._bartpho_handle: ModelHandle | None = None

    def load_chunk_summarizer(self) -> ModelHandle:
        """Nạp mô hình ViT5 Chunk Summarizer (lưu cache khi đã nạp)."""
        if self._vit5_handle is None:
            self._vit5_handle = load_seq2seq_model(VIT5_MODEL_PATH)
        return self._vit5_handle

    def load_topic_titler(self) -> ModelHandle:
        """Nạp mô hình BARTpho Topic Titler (lưu cache khi đã nạp)."""
        if self._bartpho_handle is None:
            self._bartpho_handle = load_seq2seq_model(BARTPHO_MODEL_PATH)
        return self._bartpho_handle
