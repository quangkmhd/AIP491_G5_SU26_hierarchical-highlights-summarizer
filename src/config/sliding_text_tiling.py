from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ._base import ConfigBase

Agg = Literal["mean", "max", "sum"]
Normalize = Literal["zscore", "minmax"]


class SlidingTextTilingConfig(ConfigBase):
    """Streaming Sliding TextTiling parameters."""

    block_size: int = Field(default=2, ge=1, description="BoW block size for cosine similarity")
    radii: list[int] = Field(
        default_factory=lambda: [3, 5, 10, 15, 20],
        description="peak-search radii (one depth profile per radius)",
    )
    alpha: float = Field(
        default=1.0,
        description="depth threshold = mean + alpha * std",
    )
    use_stopwords: bool = Field(
        default=True,
        description="drop Vietnamese stop words from BoW tokens",
    )
    agg: Agg = Field(default="mean", description="how to combine per-radius depth profiles")
    normalize: Normalize = Field(
        default="zscore",
        description="per-radius depth normalization",
    )
    min_segment_ratio: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
        description="minimum segment size as a fraction of n_utterances",
    )
    window_size: int = Field(
        default=40,
        ge=10,
        description="sliding window size in utterances",
    )
    stride: int = Field(
        default=5,
        ge=1,
        description="sliding window stride step size",
    )

    @model_validator(mode="after")
    def _validate_invariants(self) -> "SlidingTextTilingConfig":
        """Kiểm tra các bất biến cấu hình hợp lệ của SlidingTextTilingConfig (radii và stride)."""
        if not self.radii:
            raise ValueError("radii must be a non-empty list of positive integers")
        for r in self.radii:
            if not isinstance(r, int) or r < 1:
                raise ValueError(
                    f"each radius must be a positive integer; got {r!r}"
                )
        if self.stride >= self.window_size:
            raise ValueError(
                f"stride ({self.stride}) must be strictly less than window_size ({self.window_size})"
            )
        return self
