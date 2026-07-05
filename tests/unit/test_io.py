"""Unit tests for the shared repo _io helpers."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from src.repo._io import RepoIOError, read_json_file, write_json_file


class TestReadJsonFile(unittest.TestCase):
    def test_reads_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ok.json"
            p.write_text(json.dumps({"a": 1}), encoding="utf-8")
            self.assertEqual(read_json_file(p), {"a": 1})

    def test_raises_on_missing_file(self) -> None:
        with self.assertRaises(RepoIOError):
            read_json_file(Path("does_not_exist.json"))

    def test_raises_on_malformed_json(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fp:
            fp.write("{not json")
            bad = Path(fp.name)
        try:
            with self.assertRaises(RepoIOError):
                read_json_file(bad)
        finally:
            bad.unlink()


class TestWriteJsonFile(unittest.TestCase):
    def test_writes_payload_to_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            write_json_file(p, {"x": 2})
            self.assertEqual(json.loads(p.read_text(encoding="utf-8")), {"x": 2})

    def test_creates_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "deep" / "nested" / "out.json"
            write_json_file(p, [1, 2, 3])
            self.assertTrue(p.is_file())

    def test_no_temp_files_left_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            write_json_file(p, {"y": 3})
            # Only the final file should exist; no .tmp leftovers.
            self.assertEqual(sorted(os.listdir(tmp)), ["out.json"])

    def test_overwrites_existing_file_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            p.write_text('{"old": true}', encoding="utf-8")
            write_json_file(p, {"new": True})
            # Old content is gone, new content is in place.
            self.assertEqual(json.loads(p.read_text(encoding="utf-8")), {"new": True})

    def test_vietnamese_payload_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            payload = {"text": "Xin chào, tiếng Việt có dấu."}
            write_json_file(p, payload)
            # ensure_ascii=False keeps the Vietnamese diacritics intact.
            self.assertIn("tiếng Việt", p.read_text(encoding="utf-8"))
