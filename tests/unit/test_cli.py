"""Unit tests for the CLI runner (runtime-001+002+streaming)."""

from __future__ import annotations

import json
import os
import io
import logging
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.runtime.cli import main as cli_main
from src.service import StreamingOrchestrator


class FakeSummarizer:
    def abstractive(self, chunk, chapter_number=1, chunk_index=0):
        return f"Tóm tắt {chunk.utterances[0].index}"
    def title(self, segment, chapter_number=1):
        return f"Chủ đề {chapter_number}"


def run_cli(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    def factory():
        return StreamingOrchestrator(summarizer=FakeSummarizer())
    root = logging.getLogger()
    root_level = root.level
    handler_levels = [handler.level for handler in root.handlers]
    try:
        with mock.patch("src.runtime.cli.StreamingOrchestrator", side_effect=factory):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli_main(argv)
    finally:
        root.setLevel(root_level)
        for handler, level in zip(root.handlers, handler_levels):
            handler.setLevel(level)
    return code, stdout.getvalue(), stderr.getvalue()


def _make_transcript_file(path: Path, n_utterances: int = 10) -> None:
    data = {
        "dial_id": 0,
        "utterances": [f"Câu thoại {i}" for i in range(n_utterances)],
        "segments": [n_utterances],
    }
    path.write_text(json.dumps([data], ensure_ascii=False), encoding="utf-8")


class CliProcessTests(unittest.TestCase):
    def test_process_prints_summary(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tf = Path(tmp) / "transcript.json"
            _make_transcript_file(tf, n_utterances=8)
            old_argv = sys.argv
            try:
                sys.argv = ["cli", "process", str(tf)]
                rc, _, _ = run_cli(["process", str(tf)])
                self.assertEqual(rc, 0)
            finally:
                sys.argv = old_argv

    def test_process_with_output_file(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tf = Path(tmp) / "transcript.json"
            of = Path(tmp) / "recap.json"
            _make_transcript_file(tf, n_utterances=6)
            old_argv = sys.argv
            try:
                sys.argv = ["cli", "process", str(tf), "--output", str(of)]
                rc, _, _ = run_cli(["process", str(tf), "--output", str(of)])
                self.assertEqual(rc, 0)
                self.assertTrue(of.exists())
                recap = json.loads(of.read_text(encoding="utf-8"))
                self.assertIn("segments", recap)
                self.assertIn("meeting_id", recap)
            finally:
                sys.argv = old_argv

    def test_process_nonexistent_file_returns_nonzero(self) -> None:
        old_argv = sys.argv
        try:
            sys.argv = ["cli", "process", "/nonexistent/file.json"]
            with self.assertRaises(SystemExit) as ctx:
                cli_main()
            self.assertNotEqual(ctx.exception.code, 0)
        finally:
            sys.argv = old_argv

    def test_empty_json_array_returns_fix_message(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tf = Path(tmp) / "empty.json"
            tf.write_text("[]", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "src.runtime.cli", "process", str(tf)],
                capture_output=True,
                text=True,
                env=os.environ.copy(),
                cwd=ROOT,
                timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Fix:", result.stderr)
            self.assertIn("JSON array", result.stderr)


class CliStreamTests(unittest.TestCase):
    def test_stream_emits_ndjson(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tf = Path(tmp) / "transcript.json"
            _make_transcript_file(tf, n_utterances=8)
            code, stdout, stderr = run_cli(["stream", str(tf)])
            self.assertEqual(code, 0, msg=stderr)
            lines = [ln for ln in stdout.splitlines() if ln.strip()]
            self.assertGreater(len(lines), 0)
            # All lines should be valid NDJSON with a "type" and "payload"
            for line in lines:
                if line.startswith("#"):
                    continue
                obj = json.loads(line)
                self.assertIn("type", obj)
                self.assertIn("payload", obj)
            # At least one segment-closed event
            types = [json.loads(ln)["type"] for ln in lines if not ln.startswith("#")]
            self.assertIn("segment-closed", types)
            # Last non-comment line is meeting-completed
            self.assertEqual(types[-1], "meeting-completed")

    def test_stream_with_output_file(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tf = Path(tmp) / "transcript.json"
            of = Path(tmp) / "recap.json"
            _make_transcript_file(tf, n_utterances=6)
            code, _, stderr = run_cli(["stream", str(tf), "--output", str(of)])
            self.assertEqual(code, 0, msg=stderr)
            self.assertTrue(of.exists())
            recap = json.loads(of.read_text(encoding="utf-8"))
            self.assertIn("segments", recap)

    def test_stream_pretty(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tf = Path(tmp) / "transcript.json"
            _make_transcript_file(tf, n_utterances=8)
            code, stdout, stderr = run_cli(["stream", str(tf), "--pretty"])
            self.assertEqual(code, 0, msg=stderr)
            self.assertIn("Tóm tắt chunk:", stdout)
            self.assertIn("Chủ đề:", stdout)
            # Ensure it is not NDJSON
            for line in stdout.splitlines():
                if line.strip() and not line.startswith("Tóm tắt chunk:") and not line.startswith("Chủ đề:"):
                    try:
                        obj = json.loads(line)
                        self.assertNotIn("type", obj)
                    except json.JSONDecodeError:
                        pass
