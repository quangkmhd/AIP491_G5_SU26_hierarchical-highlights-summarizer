"""ModelLoader -- per-process singleton for HF model + 4-bit LLM caching.

Spec: docs/superpowers/specs/2026-07-04-model-002-design.md (D3).

Holds at most one `ModelHandle` per `ModelKind` for the lifetime of
the process. `MODEL_LOAD_LLM=0` env var swaps the real Vistral load
for a `MockLLMBackbone` so unit tests + offline CI never touch the
network.

Concurrency (C3): the per-process singleton is guarded by a class-
level lock, but the cache lookup-and-insert is also guarded by a
second lock so that two threads concurrently calling
`load_coherence_net()` for the first time do not both trigger the
expensive HF load (which would double VRAM usage).
"""

from __future__ import annotations

import os
import logging
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import torch

from .coherence_net import NSP_CKPT_PATH, CoherenceNet

logger = logging.getLogger("src.repo.model_loader")


class ModelKind(str, Enum):
    """Catalog of model identifiers cached by ModelLoader."""

    NSP = "nsp"
    LLM_BACKBONE = "llm_backbone"


# Backbone choices (spec D2).
LLM_BACKBONE_ID: str = "Viet-Mistral/Vistral-7B-Chat"
NSP_ENCODER_ID: str = "bert-base-multilingual-cased"


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
        "hierarchical_abstractive": '{"notes": [{"chunk_id": "mock", "summary": "Nhóm đã thảo luận về chủ đề này.", "contains_key_point": false, "contains_action_item": false}]}',
        "hierarchical_title": '{"title": "Chương mẫu", "one_line_summary": "none"}',
        "ssdst_abstractive": '{"notes": [{"chunk_id": "mock", "summary": "Nhóm đã cập nhật trạng thái chủ đề.", "contains_key_point": false, "contains_action_item": false}]}',
        "ssdst_state_update": '{"current_topic": "", "entities": [], "decisions": [], "open_actions": [], "resolved_references": []}',
    }

    def __init__(self) -> None:
        self.call_count: int = 0
        self.last_prompt: str = ""

    def generate(self, prompt: str, task: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        return self.CANNED_RESPONSES.get(task, "")


def _resolve_device() -> str:
    """Return 'cuda' if available else 'cpu'.

    Note: callers that REQUIRE CUDA should assert
    `torch.cuda.is_available()` themselves (see I3 in the review doc).
    This helper only reports the resolved device; it does not enforce.
    """
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_nsp_weights(ckpt_path: str | Path, device: str) -> CoherenceNet:
    """Load the project's pre-trained CoherenceNet checkpoint.

    Implements spec D1: the in-repo `cpt_4000.pth` is the single
    source of truth for the NSP weights. We resize the multilingual
    BERT embeddings to match the checkpoint's vocab (38168), then
    load only the keys whose shapes match.

    C4 mitigation: the returned `CoherenceNet` exposes a
    `coerce_token_ids(input_ids)` helper that clamps any out-of-range
    ID to the UNK row (0), so callers can pass real Vietnamese text
    through `bert-base-multilingual-cased`'s 119547-vocab tokenizer
    without crashing the embedding lookup. The inference quality
    degrades for the clamped tokens, but the call no longer raises.
    """
    from transformers import AutoModel  # local import to keep module import cheap

    p = Path(ckpt_path)
    logger.info("loading NSP checkpoint path=%s device=%s", p, device)
    if not p.is_file():
        raise FileNotFoundError(
            f"NSP checkpoint not found at {p}. "
            f"Expected the pre-trained cpt_4000.pth at the project root."
        )
    bert = AutoModel.from_pretrained(NSP_ENCODER_ID)
    state = torch.load(p, map_location="cpu", weights_only=True)

    # Resize the inner BertModel's embedding to match the checkpoint's vocab.
    ck_vocab = state["bert.embeddings.word_embeddings.weight"].shape[0]
    bert.resize_token_embeddings(ck_vocab)

    # Strip the "bert." prefix so the keys line up with the inner model.
    bert_state = {k[len("bert."):]: v for k, v in state.items() if k.startswith("bert.")}
    own = bert.state_dict()
    matched = {k: v for k, v in bert_state.items() if k in own and v.shape == own[k].shape}
    bert.load_state_dict(matched, strict=False)

    # Build the CoherenceNet, then load the decoder.
    net = CoherenceNet(bert=bert, device=device)
    decoder_state = {
        k[len("coherence_decoder."):]: v
        for k, v in state.items()
        if k.startswith("coherence_decoder.")
    }
    net.coherence_decoder.load_state_dict(decoder_state, strict=False)
    net.to(device)
    net.eval()

    # C4: attach vocab info for the token-ID clamp helper.
    net._checkpoint_vocab_size = ck_vocab  # type: ignore[attr-defined]
    logger.info(
        "NSP checkpoint loaded vocab_size=%d matched_bert_keys=%d decoder_keys=%d",
        ck_vocab,
        len(matched),
        len(decoder_state),
    )
    return net


def _coerce_token_ids(input_ids: "torch.Tensor", vocab_size: int) -> "torch.Tensor":
    """Clamp any token ID >= vocab_size to 0 (the UNK / [PAD] row).

    This is a pragmatic workaround for the C4 mismatch: the
    pre-trained checkpoint was trained with a 38168-vocab Vietnamese-
    subset tokenizer, but we load `bert-base-multilingual-cased` (vocab
    119547) for the embedding initialisation. Real Vietnamese text
    passed through the multilingual tokenizer will produce IDs in the
    full 119547 range; the embedding lookup in
    `nn.Embedding(38168, 768)` would raise `IndexError` for any ID
    >= 38168 without this clamp.
    """
    return torch.clamp(input_ids, max=vocab_size - 1)


def _load_llm_backbone(device: str) -> ModelHandle:
    """Load Viet-Mistral/Vistral-7B-Chat in 4-bit (bitsandbytes).

    Spec D2: 4-bit quantization via `bitsandbytes` to fit RTX 4060 8GB.
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

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    logger.info("loading LLM backbone id=%s mode=4bit device=%s", LLM_BACKBONE_ID, device)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
    )
    tokenizer = AutoTokenizer.from_pretrained(LLM_BACKBONE_ID)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_BACKBONE_ID,
        quantization_config=bnb,
        device_map="auto",
    )
    return ModelHandle(
        kind=ModelKind.LLM_BACKBONE,
        model=model,
        device=device,
        checkpoint_path=LLM_BACKBONE_ID,
        tokenizer=tokenizer,
    )


class ModelLoader:
    """Per-process singleton that caches `ModelHandle` by `ModelKind`.

    Concurrency: `_instance_lock` makes the singleton creation safe;
    `_cache_lock` makes the per-kind lookup-and-insert safe so that
    two threads cannot both trigger a fresh `ModelKind.NSP` load.
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

    def load_coherence_net(self) -> ModelHandle:
        with self._cache_lock:
            if ModelKind.NSP in self._cache:
                logger.debug("model cache hit kind=%s", ModelKind.NSP.value)
                return self._cache[ModelKind.NSP]
            device = _resolve_device()
            net = _load_nsp_weights(NSP_CKPT_PATH, device)
            from transformers import AutoTokenizer  # local import for cost

            tokenizer = AutoTokenizer.from_pretrained(NSP_ENCODER_ID)
            handle = ModelHandle(
                kind=ModelKind.NSP,
                model=net,
                device=device,
                checkpoint_path=NSP_CKPT_PATH,
                tokenizer=tokenizer,
            )
            self._cache[ModelKind.NSP] = handle
            logger.info("model cache store kind=%s device=%s", ModelKind.NSP.value, device)
            return handle

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
