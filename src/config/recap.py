from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from ._base import ConfigBase
from .abstractive import AbstractiveConfig
from .chunking import ChunkingConfig
from .language import LanguageConfig
from .sliding_text_tiling import SlidingTextTilingConfig


def _default_env_file() -> str | None:
    """Resolve the .env file path at construction time.

    Honors the MEETING_RECAP_ENV_FILE override (so tests can point at
    .env.test or set None to skip file loading entirely).

    The default ".env" is resolved relative to the project root (not CWD),
    so it works reliably in Docker containers, systemd services, and
    subprocesses with different working directories.
    """
    return os.getenv("MEETING_RECAP_ENV_FILE", str(Path(__file__).resolve().parents[2] / ".env"))


Device = Literal["auto", "cpu", "cuda"]


class MeetingRecapConfig(ConfigBase):
    """Top-level config consumed by the meeting-recap orchestrator."""

    model_config = SettingsConfigDict(
        env_prefix="MEETING_RECAP_",
        env_nested_delimiter="__",
        env_file=_default_env_file(),
        env_file_encoding="utf-8",
    )

    text_tiling: SlidingTextTilingConfig = Field(default_factory=SlidingTextTilingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    abstractive: AbstractiveConfig = Field(default_factory=AbstractiveConfig)
    language: LanguageConfig = Field(default_factory=LanguageConfig)

    device: Device = Field(
        default="auto",
        description="device resolver hint (auto prefers cuda when available)",
    )
    data_dir: Path = Field(
        default=Path("data/eval_vi"),
        description="directory containing the Vietnamese evaluation corpora",
    )
    artifacts_dir: Path = Field(
        default=Path("docs/generated"),
        description="directory for generated recap / demo artifacts",
    )