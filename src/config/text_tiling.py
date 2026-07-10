"""SlidingTextTilingConfig: parameters for the multi-scale Sliding TextTiling.

The pipeline combines a custom BoW + cosine TextTiling (depth scores, alpha
threshold) with a sliding-window idea taken from the LLM-powered Meeting
Recap paper (Asthana et al., 2025, Section 3.2.2). The paper sweeps a
window of utterances with a fixed stride and merges boundaries by
max-voting; because the BoW TextTiling is not token-bounded, the sliding
behaviour is reproduced by computing depth scores at multiple peak-search
radii and aggregating the z-scored depths.

Fields:
  * block_size: how many utterances on each side are pooled into the BoW
    blocks compared at every gap (1 = pure pairwise similarity).
  * radii: list of peak-search radii; each radius produces one depth
    profile that is z-scored before being aggregated.
  * alpha: depth threshold = mean + alpha * std. Default 0.9 matches the
    reference implementation in 16-eval-DTS.
  * use_stopwords: if True, drops Vietnamese stop words (loaded lazily).
  * agg: how to combine the per-radius depth profiles ("mean", "max",
    "sum").
  * normalize: per-radius normalization ("zscore" or "minmax").
  * min_segment_ratio: minimum segment size as a fraction of total
    utterances, used for the small-segment post-merge pass.

Cross-field rule: radii must be a non-empty list of positive integers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ._base import ConfigBase

Agg = Literal["mean", "max", "sum"]
Normalize = Literal["zscore", "minmax"]


class SlidingTextTilingConfig(ConfigBase):
    """Sliding TextTiling parameters."""

    block_size: int = Field(default=3, ge=1, description="BoW block size for cosine similarity")
    radii: list[int] = Field(
        default_factory=lambda: [3, 5, 10, 15, 20],
        description="peak-search radii (one depth profile per radius)",
    )
    alpha: float = Field(
        default=0.9,
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

    @model_validator(mode="after")
    def _radii_non_empty(self) -> "SlidingTextTilingConfig":
        if not self.radii:
            raise ValueError("radii must be a non-empty list of positive integers")
        for r in self.radii:
            if not isinstance(r, int) or r < 1:
                raise ValueError(
                    f"each radius must be a positive integer; got {r!r}"
                )
        return self
