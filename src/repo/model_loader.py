"""ModelLoader -- per-process singleton for the LLM backbone caching.

Spec: docs/superpowers/specs/2026-07-04-model-002-design.md (D3).

Holds at most one `ModelHandle` per `ModelKind` for the lifetime of
the process. `MODEL_LOAD_LLM=0` env var swaps the real gemma-4-E2B-it-qat-GGUF
load for a `MockLLMBackbone` so unit tests + offline CI never touch the
network.

The NSP-BERT CoherenceNet infrastructure was removed; topic segmentation
is now handled entirely by the lexical Sliding TextTiling in
`src/service/text_tiling.py`.
"""

from __future__ import annotations

import os
import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar


logger = logging.getLogger("src.repo.model_loader")


class ModelKind(str, Enum):
    """Catalog of model identifiers cached by ModelLoader."""

    LLM_BACKBONE = "llm_backbone"


# Backbone choices (spec D2).
LLM_BACKBONE_ID: str = "unsloth/gemma-4-E2B-it-qat-GGUF"
GGUF_MODEL_ID: str = LLM_BACKBONE_ID
GGUF_MODEL_FILENAME: str = "gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf"


@dataclass(frozen=True)
class ModelHandle:
    """A loaded model + its provenance."""

    kind: ModelKind
    model: Any
    device: str
    checkpoint_path: str | None = None
    tokenizer: Any = None


class MockLLMBackbone:
    """Offline stand-in for the Vietnamese LLM backbone.

    Records every `generate` call so tests can assert on prompt
    formatting without loading 4-bit weights.
    """

    CANNED_RESPONSES: ClassVar[dict[str, str]] = {
        "hierarchical_abstractive": "Nhóm đã thảo luận về chủ đề này.",
        "hierarchical_title": "Chương mẫu\nnone",
    }

    def __init__(self) -> None:
        self.call_count: int = 0
        self.last_prompt: str = ""

    def generate(self, prompt: str, task: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        return self.CANNED_RESPONSES.get(task, "")


class GGUFLLMBackbone:
    """Adapter wrapping a llama_cpp.Llama GGUF model into the backbone
    interface expected by HierarchicalSummarizationService.

    The generate() method formats a chat completion with JSON-constrained
    decoding and returns the assistant response text.
    """

    SYSTEM_PROMPT: str = (
        "Bạn là engine tạo meeting recap chuyên nghiệp. "
        "Luôn trả lời bằng tiếng Việt."
    )

    def __init__(self, llm: "Llama") -> None:
        self._llm = llm
        self.call_count: int = 0
        self.last_prompt: str = ""

    def generate(self, prompt: str, task: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        response = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.1,
        )
        return response["choices"][0]["message"]["content"].strip()


def _resolve_device() -> str:
    """Return 'cuda' if available else 'cpu'.

    Note: callers that REQUIRE CUDA should assert
    `torch.cuda.is_available()` themselves (see I3 in the review doc).
    This helper only reports the resolved device; it does not enforce.
    """
    return "cuda" if __import__("torch").cuda.is_available() else "cpu"


def _load_llm_backbone(device: str) -> ModelHandle:
    """Load Gemma 4 E2B GGUF via llama.cpp.

    Uses the quantized GGUF (Q4_K_XL) for efficient inference on 8GB VRAM.
    Falls back to `MockLLMBackbone` when `MODEL_LOAD_LLM=0` so
    offline unit tests can still construct a usable handle.
    """
    if os.environ.get("MODEL_LOAD_LLM", "1") == "0":
        logger.info("loading LLM backbone mode=mock MODEL_LOAD_LLM=0 device=cpu")
        return ModelHandle(
            kind=ModelKind.LLM_BACKBONE,
            model=MockLLMBackbone(),
            device="cpu",
            checkpoint_path=None,
        )

    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    logger.info("loading GGUF model id=%s filename=%s device=%s", GGUF_MODEL_ID, GGUF_MODEL_FILENAME, device)
    gguf_path = hf_hub_download(
        repo_id=GGUF_MODEL_ID,
        filename=GGUF_MODEL_FILENAME,
    )
    n_gpu_layers = -1 if device == "cuda" else 0
    llm = Llama(
        model_path=gguf_path,
        n_gpu_layers=n_gpu_layers,
        n_ctx=8192,
        verbose=False,
        flash_attn=True,
    )
    backbone = GGUFLLMBackbone(llm)
    return ModelHandle(
        kind=ModelKind.LLM_BACKBONE,
        model=backbone,
        device=device,
        checkpoint_path=gguf_path,
        tokenizer=None,
    )


class ModelLoader:
    """Per-process singleton that caches `ModelHandle` by `ModelKind`.

    Concurrency: `_instance_lock` makes the singleton creation safe;
    `_cache_lock` makes the per-kind lookup-and-insert safe so that
    two threads cannot both trigger a fresh load.
    """

    _instance: "ModelLoader | None" = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._cache: dict[ModelKind, ModelHandle] = {}
        self._cache_lock: threading.Lock = threading.Lock()

    @classmethod
    def instance(cls) -> "ModelLoader":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    # -- public API ----------------------------------------------------------

    def load_llm_backbone(self) -> ModelHandle:
        with self._cache_lock:
            if ModelKind.LLM_BACKBONE in self._cache:
                logger.debug("model cache hit kind=%s", ModelKind.LLM_BACKBONE.value)
                return self._cache[ModelKind.LLM_BACKBONE]
            device = _resolve_device()
            handle = _load_llm_backbone(device)
            self._cache[ModelKind.LLM_BACKBONE] = handle
            logger.info(
                "model cache store kind=%s device=%s checkpoint=%s",
                ModelKind.LLM_BACKBONE.value,
                handle.device,
                handle.checkpoint_path or "mock",
            )
            return handle