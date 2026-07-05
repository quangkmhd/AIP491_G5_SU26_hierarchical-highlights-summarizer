"""Runtime layer -- FastAPI server + CLI runner for the recap pipeline.

Independent of UI. May depend on types/config/repo/data/service.

Note: the default `app` is intentionally NOT bound at module level; call
`create_app()` to get one.  This keeps test imports from triggering heavy
model loads through the CoherenceScorer → ModelLoader chain.
"""

from .api import create_app
from .cli import main as cli_main

__all__ = ["create_app", "cli_main"]
