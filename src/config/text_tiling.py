"""TextTilingConfig: sliding-window TextTiling parameters (paper-1 §3.3).

Defaults are paper-anchored:
  * window_size = 30 utterances (paper-1 §3.3)
  * stride      = 10 utterances (paper-1 §3.3)
  * smoothing   = "mean"      (paper-1 §3.3 -- marked as "tune" default)
  * cutoff_policy = "mean+2std" (paper-1 §3.3)

Cross-field rule: stride <= window_size. Stride > window would skip
utterances entirely, which is invalid for a sliding-window TextTiling
pipeline.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ._base import ConfigBase

Smoothing = Literal["mean", "median", "ema"]
CutoffPolicy = Literal["mean", "mean+2std", "depth_knee"]


class TextTilingConfig(ConfigBase):
    """Sliding-window TextTiling parameters (paper-1 §3.3)."""

    window_size: int = Field(default=30, ge=1, description="paper-1 §3.3: window of N utterances")
    stride: int = Field(default=10, ge=1, description="paper-1 §3.3: slide by N utterances")
    smoothing: Smoothing = Field(
        default="mean",
        description="paper-1 §3.3 smoothing policy (tune default = mean)",
    )
    cutoff_policy: CutoffPolicy = Field(
        default="mean+2std",
        description="paper-1 §3.3 cutoff policy (tune default = mean+2std)",
    )

    @model_validator(mode="after")
    def _stride_le_window(self) -> "TextTilingConfig":
        if self.stride > self.window_size:
            raise ValueError(
                f"stride ({self.stride}) must be <= window_size ({self.window_size}); "
                "otherwise utterances would be skipped."
            )
        return self
