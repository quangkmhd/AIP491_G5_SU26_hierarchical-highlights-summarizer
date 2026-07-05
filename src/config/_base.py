"""Shared base class for every config object in src/config/.

Every sub-config inherits from `ConfigBase`, which:
  * inherits from `pydantic_settings.BaseSettings` so every field is
    env-overridable out of the box;
  * freezes the model (`frozen=True`) so a config instance can be
    safely shared across threads and across the orchestrator pipeline;
  * sets `extra="forbid"` so unknown env vars or unknown kwargs raise
    a `ConfigError` at construction time;
  * sets `case_sensitive=False` for env-var name matching;
  * sets `validate_default=True` so default values also go through
    validators (catches invalid paper-anchored defaults early).

Sub-classes that need env-var loading (e.g. `MeetingRecapConfig`)
override `model_config` to add `env_prefix`, `env_nested_delimiter`,
and `env_file`.
"""

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
