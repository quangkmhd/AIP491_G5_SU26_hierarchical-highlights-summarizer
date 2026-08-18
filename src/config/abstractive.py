from __future__ import annotations

from pydantic import Field

from ._base import ConfigBase


class AbstractiveConfig(ConfigBase):
    """Abstractive-summary context window (paper-2 §3.3, 512 tokens)."""

    context_window: int = Field(
        default=512,
        ge=1,
        description="paper-2 §3.3: surrounding context in tokens for abstractive summary",
    )
