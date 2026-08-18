from __future__ import annotations

import pydantic

ConfigError = pydantic.ValidationError
"""Typed alias of `pydantic.ValidationError` for the config layer.

Pydantic v2 raises this same class for every model-validation failure
(extra=forbid, ge/le, model_validator, etc.), so `except ConfigError`
catches all of them.
"""
