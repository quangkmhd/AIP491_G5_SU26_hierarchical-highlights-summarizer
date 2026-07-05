"""Shared IO helpers for the Repository layer.

Both `RecapRepo` and `TranscriptRepo` need to:
  * read a JSON file with utf-8 encoding and translate parse errors
    into a typed exception,
  * write a JSON file atomically so a mid-write crash does not
    corrupt the existing file.

Centralising this in one place keeps the encoding / atomicity /
error-translation contract consistent across every new repo added
in the future.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class RepoIOError(Exception):
    """Raised by `read_json_file` / `write_json_file` on any IO failure."""


def read_json_file(path: str | Path) -> Any:
    """Read and JSON-parse a file with utf-8 encoding.

    Raises:
        RepoIOError: if the file is missing or the JSON is malformed.
    """
    p = Path(path)
    if not p.is_file():
        raise RepoIOError(f"File not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except json.JSONDecodeError as exc:
        raise RepoIOError(f"Malformed JSON in {p}: {exc}") from exc


def write_json_file(path: str | Path, payload: Any) -> Path:
    """Write `payload` as JSON to `path` atomically.

    Atomicity (I1): the payload is written to a sibling temp file and
    then `os.replace`-d onto the final path. A crash mid-write leaves
    the temp file (which the next call cleans up) and the original
    `path` is never partially overwritten.

    Returns the final path.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = p.with_suffix(p.suffix + ".tmp")
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=p.suffix,
            prefix=p.stem + ".",
            dir=str(p.parent),
            delete=False,
            encoding="utf-8",
        ) as fp:
            json.dump(payload, fp, indent=2, ensure_ascii=False)
            tmp_path = Path(fp.name)
        os.replace(tmp_path, p)
    except OSError as exc:
        # Clean up the temp file if it survived.
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise RepoIOError(f"Failed to write JSON to {p}: {exc}") from exc
    return p
