from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from ._base import ConfigBase
from .chunking import ChunkingConfig
from .sliding_text_tiling import SlidingTextTilingConfig


def _default_env_file() -> str | None:
    return os.getenv("MEETING_RECAP_ENV_FILE", str(Path(__file__).resolve().parents[2] / ".env"))


Device = Literal["auto", "cpu", "cuda"]


class MeetingRecapConfig(ConfigBase):
    model_config = SettingsConfigDict(
        env_prefix="MEETING_RECAP_",
        env_nested_delimiter="__",
        env_file=_default_env_file(),
        env_file_encoding="utf-8",
    )

    text_tiling: SlidingTextTilingConfig = Field(default_factory=SlidingTextTilingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)

    device: Device = Field(
        default="auto",
        description="device resolver hint (auto prefers cuda when available)",
    )