from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigBase(BaseSettings):
    """Frozen BaseSettings shared by every config object."""

    model_config = SettingsConfigDict(
        extra="forbid",
        frozen=True,
        case_sensitive=False,
        validate_default=True,
    )
