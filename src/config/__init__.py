"""Config layer -- tunable hyper-parameters for the meeting-recap pipeline.

Public API:
    ConfigBase          -- shared frozen BaseSettings base class
    ConfigError         -- typed alias of pydantic.ValidationError
    TextTilingConfig    -- sliding-window TextTiling parameters (paper-1 §3.3)
    ChunkingConfig      -- 8-utterance hierarchical chunking (paper-2 §3.3)
    AbstractiveConfig   -- abstractive context window (512 tokens, paper-2 §3.3)
    LanguageConfig      -- BCP-47 tag + per-language model variant
    MeetingRecapConfig  -- composes all of the above; reads .env with prefix
                           MEETING_RECAP_ and nested delimiter __

Note (config-001+, D2): HighlightsConfig was removed because the highlights
pipeline (DR1) is out of scope per the 2026-07-05 design decision.
"""

from __future__ import annotations

from ._base import ConfigBase
from .abstractive import AbstractiveConfig
from .chunking import ChunkingConfig
from .errors import ConfigError
from .language import LanguageConfig
from .recap import MeetingRecapConfig
from .text_tiling import TextTilingConfig

__all__ = [
    "ConfigBase",
    "ConfigError",
    "TextTilingConfig",
    "ChunkingConfig",
    "AbstractiveConfig",
    "LanguageConfig",
    "MeetingRecapConfig",
]
