from dataclasses import dataclass, field
import os
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
TOOL_DIR = APP_DIR.parent
FRONTEND_DIR = TOOL_DIR / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _str_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class AppSettings:
    request_timeout_seconds: float = field(default_factory=lambda: _float_env("LLM_TIMEOUT", 180.0))
    retry_attempts: int = 3
    ollama_autostart_enabled: bool = field(default_factory=lambda: _bool_env("OLLAMA_AUTOSTART", True))
    ollama_stop_after_run: bool = field(default_factory=lambda: _bool_env("OLLAMA_STOP_AFTER_RUN", True))
    ollama_startup_timeout_seconds: float = field(default_factory=lambda: _float_env("OLLAMA_STARTUP_TIMEOUT", 20.0))
    ollama_stop_timeout_seconds: float = field(default_factory=lambda: _float_env("OLLAMA_STOP_TIMEOUT", 10.0))
    recap_normalize_transcript: bool = field(default_factory=lambda: _bool_env("RECAP_NORMALIZE_TRANSCRIPT", False))
    recap_normalize_model: str = field(default_factory=lambda: _str_env("RECAP_NORMALIZE_MODEL", "gemma4:12b-it-qat"))
    recap_normalize_base_url: str = field(default_factory=lambda: _str_env("RECAP_NORMALIZE_BASE_URL", "http://127.0.0.1:11434"))
