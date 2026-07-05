"""End-to-end smoke test for the config layer (config-001).

This is a runnable sanity check, NOT production code. It proves that:

  1. Default MeetingRecapConfig composes 5 sub-configs with paper defaults.
  2. A custom .env.test file overrides via MEETING_RECAP_<SUB>__<FIELD>.
  3. Process env vars beat .env file values.
  4. _env_file=None skips the file.
  5. Invalid cross-field combos raise ConfigError (which is ValidationError).
  6. The resulting config plugs into model-001 types: chunking.chunk_size
     bounds the number of utterances per Chunk.
  7. Unknown env vars are silently ignored (Pydantic-Settings default).

Run with:

    python tests/manual/test_config_end_to_end.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.config import (
    ChunkingConfig,
    ConfigError,
    LanguageConfig,
    MeetingRecapConfig,
    TextTilingConfig,
)
from src.types import Chunk, TranscriptIngestionRequest


def _clear_recap_env() -> None:
    for k in [k for k in os.environ if k.upper().startswith("MEETING_RECAP_")]:
        del os.environ[k]


class DefaultsFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_default_compose_matches_paper(self) -> None:
        cfg = MeetingRecapConfig(_env_file=None)
        self.assertEqual(cfg.text_tiling.window_size, 30)
        self.assertEqual(cfg.text_tiling.stride, 10)
        self.assertEqual(cfg.chunking.chunk_size, 8)
        self.assertEqual(cfg.abstractive.context_window, 512)
        self.assertEqual(cfg.language.tag, "vi")


class DotEnvOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_dotenv_test_loads_correctly(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env.test", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=12\n")
            f.write("MEETING_RECAP_TEXT_TILING__STRIDE=20\n")
            env_path = f.name
        try:
            cfg = MeetingRecapConfig(_env_file=env_path)
            self.assertEqual(cfg.chunking.chunk_size, 12)
            self.assertEqual(cfg.text_tiling.stride, 20)
        finally:
            os.unlink(env_path)
            _clear_recap_env()

    def test_env_var_beats_dotenv(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env.test", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=12\n")
            env_path = f.name
        os.environ["MEETING_RECAP_CHUNKING__CHUNK_SIZE"] = "16"
        try:
            cfg = MeetingRecapConfig(_env_file=env_path)
            self.assertEqual(cfg.chunking.chunk_size, 16)
        finally:
            os.unlink(env_path)
            _clear_recap_env()

    def test_env_file_none_skips_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env.test", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=99\n")
            env_path = f.name
        try:
            cfg = MeetingRecapConfig(_env_file=None)
            self.assertEqual(cfg.chunking.chunk_size, 8)  # default
        finally:
            os.unlink(env_path)
            _clear_recap_env()


class CrossFieldRejectionTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_stride_gt_window_raises(self) -> None:
        with self.assertRaises(ConfigError):
            MeetingRecapConfig(
                _env_file=None,
                text_tiling=TextTilingConfig(window_size=10, stride=20),
            )

    def test_overlap_ge_chunk_size_raises(self) -> None:
        with self.assertRaises(ConfigError):
            MeetingRecapConfig(
                _env_file=None,
                chunking=ChunkingConfig(chunk_size=8, overlap=8),
            )

    def test_tag_variant_mismatch_raises(self) -> None:
        with self.assertRaises(ConfigError):
            MeetingRecapConfig(
                _env_file=None,
                language=LanguageConfig(tag="vi", model_variant="bert-base-chinese"),
            )


class Model001RoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_chunk_size_bounds_chunks(self) -> None:
        # Read the first Vietnamese dialogue (same pattern as
        # tests/manual/test_meeting_committee_sample.py for model-001).
        with (REPO_ROOT / "data" / "eval_vi" / "meeting_committee.json").open() as f:
            dialogues = json.load(f)
        assert dialogues, "expected at least one dialogue in meeting_committee.json"
        sample = dialogues[0]
        request = TranscriptIngestionRequest(
            meeting_title=f"Committee Meeting {sample['dial_id']}",
            flat_texts=sample["utterances_vi"],
            language="vi",
        )
        transcript = request.materialize()

        # Apply the config and chunk accordingly.
        cfg = MeetingRecapConfig(_env_file=None, chunking=ChunkingConfig(chunk_size=8))
        utts = transcript.utterances
        chunks = [
            Chunk(utterances=utts[i : i + cfg.chunking.chunk_size])
            for i in range(0, len(utts), cfg.chunking.chunk_size)
        ]
        # Every chunk respects the cap.
        self.assertTrue(all(len(c.utterances) <= cfg.chunking.chunk_size for c in chunks))
        # At least one chunk hits the cap (370 utt / 8 = 46 full + 1 partial).
        self.assertTrue(any(len(c.utterances) == cfg.chunking.chunk_size for c in chunks))


class ExtraForbidTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_unknown_top_level_env_var_silently_ignored(self) -> None:
        # Pydantic-Settings treats unknown env vars as "ignore" by
        # default; the contract is "env only sets existing fields".
        os.environ["MEETING_RECAP_BLOOPER"] = "1"
        try:
            cfg = MeetingRecapConfig(_env_file=None)
            # Defaults still apply; the bogus env var is silently dropped.
            self.assertEqual(cfg.chunking.chunk_size, 8)
        finally:
            _clear_recap_env()


if __name__ == "__main__":
    unittest.main(verbosity=2)
