from __future__ import annotations

from pydantic import Field, model_validator

from ._base import ConfigBase


class ChunkingConfig(ConfigBase):
    """Hierarchical chunking parameters (paper-2 §3.3)."""

    chunk_size: int = Field(default=8, ge=1, description="paper-2 §3.3: 8 utterances per chunk")
    overlap: int = Field(default=0, ge=0, description="optional overlap between consecutive chunks")

    @model_validator(mode="after")
    def _overlap_lt_chunk(self) -> "ChunkingConfig":
        if self.overlap >= self.chunk_size:
            raise ValueError(
                f"overlap ({self.overlap}) must be < chunk_size ({self.chunk_size}); "
                "an overlap >= chunk_size would mean no progress between chunks."
            )
        return self
