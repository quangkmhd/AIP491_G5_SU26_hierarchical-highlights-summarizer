"""Smoke test: load CoherenceNet from the project's NSP checkpoint.

Run with:

    MODEL_LOAD_LLM=0 python3 -m src.repo.smoke_loader
    # Optional: REQUIRE_CUDA=1 to make the smoke test fail on CPU-only hosts.

Exits 0 on success, prints the device + parameter count. This is the
verification target for the active execution plan
(`docs/exec-plans/active/model-002-model-loader.md`).

I3: when `REQUIRE_CUDA=1` is set, the smoke loader asserts the
resolved device is `cuda`; otherwise it just logs it. The default
behaviour is intentionally permissive so CPU-only CI runs do not
break.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import torch

from src.repo import (
    LLMTask,
    ModelLoader,
    get_prompt,
)
from src.repo.coherence_net import NSP_CKPT_PATH

logger = logging.getLogger("src.repo.smoke_loader")


def _count_params(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(message)s",
    )
    logger.info("NSP_CKPT_PATH = %s", NSP_CKPT_PATH)
    if not Path(NSP_CKPT_PATH).is_file():
        logger.error("checkpoint missing at %s", NSP_CKPT_PATH)
        return 1

    loader = ModelLoader.instance()
    handle = loader.load_coherence_net()
    logger.info(
        "loaded NSP on device=%s, params=%d",
        handle.device,
        _count_params(handle.model),
    )

    # I3: optional strict device check.
    if os.environ.get("REQUIRE_CUDA", "0") == "1" and handle.device != "cuda":
        logger.error(
            "REQUIRE_CUDA=1 but resolved device=%s (CUDA available: %s)",
            handle.device,
            torch.cuda.is_available(),
        )
        return 2

    # Sanity: prompts are present.
    for task in LLMTask:
        prompt = get_prompt(task)
        assert prompt.strip(), f"empty prompt for {task}"
    logger.info("4 Vietnamese prompt templates loaded")

    # LLM load (offline by default in this smoke run).
    if os.environ.get("MODEL_LOAD_LLM", "0") == "0":
        llm_handle = loader.load_llm_backbone()
        logger.info("LLM_BACKBONE offline mock returned: kind=%s", llm_handle.kind)
    else:
        logger.info("skipped LLM_BACKBONE real load (set MODEL_LOAD_LLM=0 for offline)")

    logger.info("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
