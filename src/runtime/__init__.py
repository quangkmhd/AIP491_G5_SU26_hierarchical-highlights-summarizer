"""Runtime layer -- FastAPI server + CLI runner for the recap pipeline.

Independent of UI. May depend on types/config/repo/data/service.
"""

from .api import app, create_app
from .cli import main as cli_main

__all__ = ["app", "create_app", "cli_main"]
