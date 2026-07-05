"""Typed alias of `pydantic.ValidationError` for the config layer.

Pydantic raises `ValidationError` whenever a model fails to construct
(validators, type coercion, `extra="forbid"`, etc.). The config layer
re-exports that same exception under the name `ConfigError` so call
sites can write `except ConfigError` and still receive the full
Pydantic `.errors()` payload (used by `runtime-001` for FastAPI 422
responses).

Sub-classing keeps the alias typed (it is *the* `ValidationError`,
not a wrapper), so `isinstance(e, ConfigError)` and
`isinstance(e, ValidationError)` are both true.
"""

from __future__ import annotations

import pydantic


class ConfigError(pydantic.ValidationError):
    """Typed alias of `pydantic.ValidationError` for the config layer."""
