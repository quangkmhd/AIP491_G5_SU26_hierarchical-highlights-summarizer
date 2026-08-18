from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Project-wide base for all data models in the Types layer.

    Rules enforced everywhere:
        - `extra="forbid"`: unknown fields raise a validation error so typos
          surface immediately instead of silently round-tripping.
        - `populate_by_name=True`: alias-based construction stays possible.
        - `str_strip_whitespace=True`: free-text fields are trimmed by default.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )
