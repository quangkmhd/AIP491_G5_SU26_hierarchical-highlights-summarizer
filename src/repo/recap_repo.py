"""RecapRepo -- round-trip HierarchicalRecap as canonical Pydantic JSON.

Spec: docs/superpowers/specs/2026-07-04-model-002-design.md (D6).

Wire format is the canonical Pydantic v2 dump (model_dump_json),
which preserves UUIDs as strings, datetimes as ISO 8601, and nested
models as objects. Round-trip is verified by `recap ==
RecapRepo.read(RecapRepo.write(recap, p))` for any valid recap.

Write is atomic (I1): the model's JSON string is written to a
sibling temp file and then `os.replace`-d onto the final path. A
crash mid-write leaves the original `path` untouched.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from src.types.hierarchical_recap import HierarchicalRecap

from ._io import RepoIOError, read_json_file


class RecapRepoError(Exception):
    """Raised when a recap file cannot be read, written, or validated."""


# Accepted file extensions for recap JSON files.
_VALID_EXTENSIONS: frozenset[str] = frozenset({".json"})
logger = logging.getLogger("src.repo.recap_repo")


class RecapRepo:
    """Read/write `HierarchicalRecap` objects as local JSON files."""

    def write(self, recap: HierarchicalRecap, path: str | Path) -> Path:
        """Ghi đối tượng HierarchicalRecap xuống file JSON một cách an toàn (atomic write)."""
        p = Path(path)
        self._check_extension(p)
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
                fp.write(recap.model_dump_json(indent=2))
                tmp_path = Path(fp.name)
            os.replace(tmp_path, p)
            logger.info(
                "recap written path=%s segments=%d chunks=%d",
                p,
                len(recap.segments),
                sum(len(segment.chunks) for segment in recap.segments),
            )
        except OSError as exc:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise RecapRepoError(f"Failed to write recap to {p}: {exc}") from exc
        return p

    def read(self, path: str | Path) -> HierarchicalRecap:
        """Đọc và kiểm định dữ liệu JSON từ file thành đối tượng HierarchicalRecap."""
        p = Path(path)
        self._check_extension(p)
        try:
            raw = read_json_file(p)
        except RepoIOError as exc:
            raise RecapRepoError(str(exc)) from exc
        try:
            recap = HierarchicalRecap.model_validate(raw)
        except ValidationError as exc:
            raise RecapRepoError(
                f"Recap at {p} failed Pydantic validation: {exc}"
            ) from exc
        logger.info("recap read path=%s segments=%d", p, len(recap.segments))
        return recap

    @staticmethod
    def _check_extension(p: Path) -> None:
        """Kiểm tra định dạng đuôi file xem có phải là file .json hay không."""
        if p.suffix.lower() not in _VALID_EXTENSIONS:
            raise RecapRepoError(
                f"Recap file must have a .json extension, got {p.suffix!r} ({p})"
            )
