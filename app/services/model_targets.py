from dataclasses import dataclass


LOCAL_OLLAMA_MODEL = "qwen3.5:4b-q4_K_M"
LOCAL_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_LLM_MAX_WORKERS = 1


@dataclass(frozen=True)
class ModelTarget:
    model: str
    base_url: str | None = None


def load_local_model_target() -> ModelTarget:
    return ModelTarget(
        model=LOCAL_OLLAMA_MODEL,
        base_url=LOCAL_OLLAMA_BASE_URL,
    )


def model_stage_max_workers(targets: list[ModelTarget]) -> int | None:
    if not targets:
        return None
    import os
    try:
        return max(1, int(os.getenv("LLM_MAX_WORKERS", str(DEFAULT_LLM_MAX_WORKERS))))
    except (ValueError, TypeError):
        return DEFAULT_LLM_MAX_WORKERS


def target_label(target: object) -> str:
    if isinstance(target, ModelTarget):
        return target.model
    return str(target)


def target_public_dict(target: ModelTarget) -> dict[str, str]:
    return {
        "model": target.model,
        "base_url": target.base_url or "",
    }
