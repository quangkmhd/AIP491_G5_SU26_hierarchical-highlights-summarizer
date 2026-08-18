from __future__ import annotations

import json
import logging
import threading
from enum import Enum
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

logger = logging.getLogger("src.repo.model_loader")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNK_SUMMARIZER_PATH = PROJECT_ROOT / "models" / "vit5-chunk-summarizer-v1"
TOPIC_TITLER_PATH = (
    PROJECT_ROOT / "models" / "bartpho-topic-titler-v2" / "checkpoint-230"
)


class ModelKind(str, Enum):
    CHUNK_SUMMARIZER = "chunk_summarizer"
    TOPIC_TITLER = "topic_titler"


class ModelLoadError(RuntimeError):
    """A local model cannot be loaded with its required runtime contract."""


class ModelHandle:
    def __init__(
        self,
        kind: ModelKind,
        model: Any,
        tokenizer: Any,
        device: str,
        checkpoint_path: str,
    ) -> None:
        self.kind = kind
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.checkpoint_path = checkpoint_path


REQUIRED_FILES = {
    ModelKind.CHUNK_SUMMARIZER: {
        "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json",
    },
    ModelKind.TOPIC_TITLER: {
        "config.json", "model.safetensors", "dict.txt", "sentencepiece.bpe.model", "tokenizer_config.json",
    },
}


def _tokenizer_compat_kwargs(path: Path) -> dict[str, Any]:
    """Chuẩn hóa tham số cấu hình tokenizer cũ cho tương thích với Transformers mới."""
    config_path = path / "tokenizer_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if isinstance(config.get("extra_special_tokens"), list):
        return {"extra_special_tokens": {}}
    return {}


def _load_seq2seq_handle(kind: ModelKind, path: Path) -> ModelHandle:
    """Nạp mô hình seq2seq và tokenizer từ đĩa lên GPU CUDA."""
    if not torch.cuda.is_available():
        raise ModelLoadError(
            "CUDA is unavailable; fix: run the recap service on the configured CUDA host"
        )
    missing = sorted(name for name in REQUIRED_FILES[kind] if not (path / name).is_file())
    if missing:
        raise ModelLoadError(
            f"{kind.value} checkpoint is incomplete at {path}; missing={missing}; "
            "fix: copy the complete inference artifact set"
        )
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            path,
            local_files_only=True,
            use_fast=True,
            **_tokenizer_compat_kwargs(path),
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True)
        model.to("cuda")
        model.eval()
    except Exception as exc:
        raise ModelLoadError(
            f"failed to load {kind.value} from {path}: {exc}; "
            "fix: verify CUDA memory and the complete local inference artifacts"
        ) from exc
    return ModelHandle(kind, model, tokenizer, "cuda", str(path))


_global_loader_instance: ModelLoader | None = None
_global_loader_lock: threading.Lock = threading.Lock()


def get_model_loader() -> ModelLoader:
    global _global_loader_instance
    with _global_loader_lock:
        if _global_loader_instance is None:
            _global_loader_instance = ModelLoader()
        return _global_loader_instance


def reset_model_loader() -> None:
    global _global_loader_instance
    with _global_loader_lock:
        _global_loader_instance = None


class ModelLoader:
    def __init__(self) -> None:
        """Khởi tạo đối tượng nạp mô hình ModelLoader và bộ nhớ đệm cache."""
        self._cache: dict[ModelKind, ModelHandle] = {}
        self._cache_lock = threading.Lock()

    def _load(self, kind: ModelKind, path: Path) -> ModelHandle:
        """Quản lý việc nạp mô hình vào cache hoặc lấy từ cache ra."""
        with self._cache_lock:
            if kind not in self._cache:
                self._cache[kind] = _load_seq2seq_handle(kind, path)
                if kind == ModelKind.CHUNK_SUMMARIZER:
                    logger.info("Summary Model loaded: ViT5 Chunk Summarizer (ViT5-base fine-tuned) [checkpoint=%s]", path)
                elif kind == ModelKind.TOPIC_TITLER:
                    logger.info("Title Model loaded: BARTpho Topic Titler (BARTpho-syllable fine-tuned) [checkpoint=%s]", path)
                else:
                    logger.info("model cache store kind=%s checkpoint=%s", kind.value, path)
            return self._cache[kind]

    def load_chunk_summarizer(self) -> ModelHandle:
        """Nạp mô hình ViT5 Chunk Summarizer."""
        return self._load(ModelKind.CHUNK_SUMMARIZER, CHUNK_SUMMARIZER_PATH)

    def load_topic_titler(self) -> ModelHandle:
        """Nạp mô hình BARTpho Topic Titler."""
        return self._load(ModelKind.TOPIC_TITLER, TOPIC_TITLER_PATH)
