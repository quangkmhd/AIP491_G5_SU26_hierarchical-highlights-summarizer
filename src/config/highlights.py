"""HighlightsConfig: extractive-highlight window (paper-2 §3.3, 106 tokens).

Default: extractive_window = 10 utterances.
Paper-2 §3.3 ties this to "~106 tokens" via the 1 token = 0.75 words
heuristic; the configuration stores the utterance count and leaves the
token projection to the service layer.
"""

from __future__ import annotations

from pydantic import Field

from ._base import ConfigBase


class HighlightsConfig(ConfigBase):
    """Extractive-highlight window size (paper-2 §3.3)."""

    extractive_window: int = Field(
        default=10,
        ge=1,
        description="paper-2 §3.3: extractive window in utterances (~106 tokens)",
    )
