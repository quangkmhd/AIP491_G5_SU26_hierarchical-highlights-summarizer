"""TextTilingConfig: TextTiling parameters (paper-1 §3.3).

Defaults are paper-anchored:
  * window_size = 30 utterances (paper-1 §3.3)
  * stride      = 10 utterances (paper-1 §3.3)
  * smoothing   = "mean"      (paper-1 §3.3 -- marked as "tune" default)
  * alpha       = 0.0         (paper-1 §3.3: threshold = mean + alpha * std)

In the paper, alpha is tuned on a dev set via grid search over
[-2, 2] with step 0.1 (segment.py:111). Default alpha=0 means
threshold = mean(depths).

Cross-field rule: stride <= window_size. Stride > window would skip
utterances entirely, which is invalid for a sliding-window TextTiling
pipeline.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ._base import ConfigBase

Smoothing = Literal["mean", "median", "ema"]


class TextTilingConfig(ConfigBase):
    """TextTiling parameters (paper-1 §3.3)."""

    window_size: int = Field(default=30, ge=1, description="paper-1 §3.3: window of N utterances")
    stride: int = Field(default=10, ge=1, description="paper-1 §3.3: slide by N utterances")
    smoothing: Smoothing = Field(
        default="mean",
        description="paper-1 §3.3 smoothing policy (tune default = mean)",
    )
    alpha: float = Field(
        default=1.0,
        description="paper-1 §3.3: threshold = mean + alpha * std; tuned on dev set [-2, 2]",
    )

    @model_validator(mode="after")
    def _stride_le_window(self) -> "TextTilingConfig":
        if self.stride > self.window_size:
            raise ValueError(
                f"stride ({self.stride}) must be <= window_size ({self.window_size}); "
                "otherwise utterances would be skipped."
            )
        return self
