"""Unit tests for the CLI runner (runtime-001+002+streaming)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MODEL_LOAD_LLM", "0")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.runtime.cli import main as cli_main


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
                rc = cli_main()
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
                rc = cli_main()
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


class CliStreamTests(unittest.TestCase):
    def test_stream_emits_ndjson(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tf = Path(tmp) / "transcript.json"
            _make_transcript_file(tf, n_utterances=8)
            # Use subprocess to capture stdout
            env = os.environ.copy()
            env["MODEL_LOAD_LLM"] = "0"
            result = subprocess.run(
                [sys.executable, "-m", "src.runtime.cli", "stream", str(tf)],
                capture_output=True,
                text=True,
                env=env,
                cwd=ROOT,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
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
            env = os.environ.copy()
            env["MODEL_LOAD_LLM"] = "0"
            result = subprocess.run(
                [sys.executable, "-m", "src.runtime.cli", "stream", str(tf), "--output", str(of)],
                capture_output=True,
                text=True,
                env=env,
                cwd=ROOT,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(of.exists())
            recap = json.loads(of.read_text(encoding="utf-8"))
            self.assertIn("segments", recap)
