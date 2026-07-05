"""Unit tests for RecapRepo round-trip of HierarchicalRecap JSON."""

import json
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from src.repo.recap_repo import RecapRepo, RecapRepoError
from src.types import (
    Chunk,
    DialogueTranscript,
    HierarchicalRecap,
    SegmentResult,
    Utterance,
)


def _make_recap() -> HierarchicalRecap:
    utts = [
        Utterance(speaker="S1", text=f"câu {i}", index=i) for i in range(3)
    ]
    chunk = Chunk(utterances=utts)
    seg = SegmentResult(
        title="Chương 1",
        chunks=[chunk],
        utterances_start=0,
        utterances_end=2,
    )
    return HierarchicalRecap(
        meeting_id=UUID("00000000-0000-0000-0000-000000000001"),
        segments=[seg],
        meeting_title="Cuộc họp mẫu",
    )


class TestRecapRepoRoundTrip(unittest.TestCase):
    def test_write_then_read_returns_equal_object(self) -> None:
        repo = RecapRepo()
        recap = _make_recap()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "recap.json"
            repo.write(recap, p)
            again = repo.read(p)
        self.assertEqual(again, recap)

    def test_written_file_is_valid_json(self) -> None:
        repo = RecapRepo()
        recap = _make_recap()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "recap.json"
            repo.write(recap, p)
            raw = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(raw["meeting_title"], "Cuộc họp mẫu")
        self.assertEqual(len(raw["segments"]), 1)
        self.assertEqual(raw["segments"][0]["title"], "Chương 1")

    def test_write_creates_parent_dirs(self) -> None:
        repo = RecapRepo()
        recap = _make_recap()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "nested" / "deeper" / "recap.json"
            repo.write(recap, p)
            self.assertTrue(p.is_file())


class TestRecapRepoErrors(unittest.TestCase):
    def test_read_missing_file_raises_typed_error(self) -> None:
        with self.assertRaises(RecapRepoError):
            RecapRepo().read(Path("does_not_exist.json"))

    def test_read_malformed_json_raises_typed_error(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fp:
            fp.write("{not json")
            bad = Path(fp.name)
        try:
            with self.assertRaises(RecapRepoError):
                RecapRepo().read(bad)
        finally:
            bad.unlink()

    def test_read_invalid_pydantic_raises_typed_error(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fp:
            # meeting_id is required but missing.
            json.dump({"segments": [{"chunks": "not-a-list"}]}, fp)
            bad = Path(fp.name)
        try:
            with self.assertRaises(RecapRepoError):
                RecapRepo().read(bad)
        finally:
            bad.unlink()

    def test_meeting_id_round_trips_as_uuid(self) -> None:
        repo = RecapRepo()
        recap = _make_recap()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "recap.json"
            repo.write(recap, p)
            again = repo.read(p)
        self.assertEqual(again.meeting_id, recap.meeting_id)
        self.assertIsInstance(again.meeting_id, UUID)


if __name__ == "__main__":
    unittest.main()


class TestRecapRepoExtensionValidation(unittest.TestCase):
    def test_read_rejects_non_json_extension(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as fp:
            fp.write("{}")
            bad = Path(fp.name)
        try:
            with self.assertRaises(RecapRepoError) as cm:
                RecapRepo().read(bad)
            self.assertIn("extension", str(cm.exception).lower())
        finally:
            bad.unlink()

    def test_write_rejects_non_json_extension(self) -> None:
        repo = RecapRepo()
        recap = _make_recap()
        with self.assertRaises(RecapRepoError):
            repo.write(recap, Path("/tmp/recap.txt"))


class TestRecapRepoAtomicWrite(unittest.TestCase):
    """I1: RecapRepo.write is atomic -- a mid-write crash cannot leave a
    truncated file at the destination path. The shared `write_json_file`
    helper writes to a sibling temp file and then `os.replace`s it.
    """

    def test_no_temp_files_left_in_parent_dir(self) -> None:
        import os
        repo = RecapRepo()
        recap = _make_recap()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "atomic.json"
            repo.write(recap, p)
            # Only the final file should be in the directory.
            self.assertEqual(sorted(os.listdir(tmp)), ["atomic.json"])

    def test_overwrite_does_not_leak_old_content(self) -> None:
        repo = RecapRepo()
        recap_v1 = _make_recap()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "recap.json"
            repo.write(recap_v1, p)
            recap_v2 = _make_recap()
            repo.write(recap_v2, p)
            again = repo.read(p)
        # The read-back object matches the second write, not the first.
        self.assertEqual(again, recap_v2)
