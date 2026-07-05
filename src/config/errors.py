"""Typed alias of `pydantic.ValidationError` for the config layer.

Pydantic v2's `ValidationError` is implemented in Rust and raised
directly by `pydantic_core`. Python subclasses of it do NOT match
`isinstance` against the runtime class (the Rust core constructs
exceptions of the exact class, bypassing `__init_subclass__`). For
that reason, the spec's "subclass" approach is implemented as a
module-level alias instead: `ConfigError is pydantic.ValidationError`.

Call sites can still write `except ConfigError` and receive the full
`.errors()` payload (used by `runtime-001` for FastAPI 422 responses).
The name `ConfigError` exists so the config layer has a typed catch
that reads as its own concept at call sites.
"""

from __future__ import annotations

import pydantic

ConfigError = pydantic.ValidationError
"""Typed alias of `pydantic.ValidationError` for the config layer.

Pydantic v2 raises this same class for every model-validation failure
(extra=forbid, ge/le, model_validator, etc.), so `except ConfigError`
catches all of them.
"""
