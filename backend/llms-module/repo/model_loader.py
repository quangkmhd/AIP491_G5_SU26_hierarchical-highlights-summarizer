from __future__ import annotations
from pathlib import Path
from typing import Any
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODULE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = MODULE_ROOT.parent.parent
VIT5_MODEL_PATH = MODULE_ROOT / "models" / "vit5-chunk-summarizer-v1"
BARTPHO_MODEL_PATH = MODULE_ROOT / "models" / "bartpho-topic-titler-v2" / "checkpoint-230"


def load_seq2seq_model(path: Path) -> ModelHandle:
    """Load a Seq2Seq Transformer model and Tokenizer from a local path."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    path_str = str(path.resolve())
    tokenizer = AutoTokenizer.from_pretrained(path_str, local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(path_str, local_files_only=True)
    model.to(device)
    model.eval()
    return ModelHandle(model=model, tokenizer=tokenizer, device=device)


class ModelHandle:
    """Container for loaded PyTorch model, Tokenizer, and target device."""
    def __init__(self, model: Any, tokenizer: Any, device: str) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.device = device


class ModelLoader:
    """Manages loading and caching of ViT5 and BARTpho models."""

    def __init__(self) -> None:
        self._vit5_handle: ModelHandle | None = None
        self._bartpho_handle: ModelHandle | None = None

    def load_chunk_summarizer(self) -> ModelHandle:
        """Load ViT5 Chunk Summarizer model (cached after initial load)."""
        if self._vit5_handle is None:
            self._vit5_handle = load_seq2seq_model(VIT5_MODEL_PATH)
        return self._vit5_handle

    def load_topic_titler(self) -> ModelHandle:
        """Load BARTpho Topic Titler model (cached after initial load)."""
        if self._bartpho_handle is None:
            self._bartpho_handle = load_seq2seq_model(BARTPHO_MODEL_PATH)
        return self._bartpho_handle

