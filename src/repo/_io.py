from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class RepoIOError(Exception):
    """Raised by `read_json_file` / `write_json_file` on any IO failure."""


def read_json_file(path: str | Path) -> Any:
    """Đọc và giải mã dữ liệu file JSON với chuẩn mã hóa UTF-8."""
    p = Path(path)
    if not p.is_file():
        raise RepoIOError(f"File not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except json.JSONDecodeError as exc:
        raise RepoIOError(f"Malformed JSON in {p}: {exc}") from exc


def write_json_file(path: str | Path, payload: Any) -> Path:
    """Ghi dữ liệu JSON xuống đường dẫn một cách an toàn (atomic write)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
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
