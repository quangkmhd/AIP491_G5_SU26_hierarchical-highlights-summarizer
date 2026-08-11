"""Configuration for the opt-in Custom_10h browser demo."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from ._base import ConfigBase

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DemoConfig(ConfigBase):
    """Environment-backed settings for demo-only HTTP routes."""

    model_config = ConfigBase.model_config | {"env_prefix": "DEMO_"}

    enabled: bool = False
    data_dir: str = str(
        _PROJECT_ROOT / "training-eval-suite" / "data" / "Custom_10h"
    )
    duration_seconds: float = Field(default=3600.0, gt=0.0, le=3600.0)
    gap_seconds: float = Field(default=0.65, ge=0.5, le=2.0)
