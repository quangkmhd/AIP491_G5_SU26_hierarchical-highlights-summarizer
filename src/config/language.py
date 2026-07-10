"""LanguageConfig: BCP-47 tag + per-language model variant.

The project extends paper-1 (which supports en/zh) to Vietnamese ("vi").
Default: tag="vi" with the Vietnamese BERT base
("FPTAI/vibert-base-cased").

The model_variant choices are kept as a small closed set so a
mismatched (tag, variant) pair is rejected at config construction
time, not at model load time.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ._base import ConfigBase

LanguageTag = Literal["vi", "en", "zh"]
ModelVariant = Literal["FPTAI/vibert-base-cased", "bert-base-multilingual-cased", "bert-base-chinese"]


class LanguageConfig(ConfigBase):
    """BCP-47 language tag + the per-language model variant to load."""

    tag: LanguageTag = Field(default="vi", description="BCP-47 tag (project default = vi)")
    model_variant: ModelVariant = Field(
        default="FPTAI/vibert-base-cased",
        description="HuggingFace model id to use for this language",
    )

    @model_validator(mode="after")
    def _tag_matches_variant(self) -> "LanguageConfig":
        chinese = self.model_variant == "bert-base-chinese"
        if self.tag == "zh" and not chinese:
            raise ValueError(
                "tag='zh' requires model_variant='bert-base-chinese'."
            )
        if self.tag in ("en", "vi") and chinese:
            raise ValueError(
                f"tag='{self.tag}' requires a non-chinese model_variant."
            )
        return self
