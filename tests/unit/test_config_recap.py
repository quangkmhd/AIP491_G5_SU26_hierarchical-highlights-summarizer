"""Unit tests for MeetingRecapConfig (compose + env loading)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pydantic

from src.config import (
    ConfigBase,
    MeetingRecapConfig,
    TextTilingConfig,
)
from src.config.errors import ConfigError


def _clear_recap_env() -> None:
    """Remove every MEETING_RECAP_* env var (case-insensitive) for a clean test."""
    for k in [k for k in os.environ if k.upper().startswith("MEETING_RECAP_")]:
        del os.environ[k]


class ComposeTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_defaults_match_sub_config_defaults(self) -> None:
        cfg = MeetingRecapConfig(_env_file=None)
        self.assertEqual(cfg.text_tiling.window_size, 30)
        self.assertEqual(cfg.text_tiling.stride, 10)
        self.assertEqual(cfg.chunking.chunk_size, 8)
        self.assertEqual(cfg.chunking.overlap, 0)
        # HighlightsConfig removed in config-001+ (D2).
        self.assertEqual(cfg.abstractive.context_window, 512)
        self.assertEqual(cfg.language.tag, "vi")
        self.assertEqual(cfg.language.model_variant, "bert-base-multilingual-cased")
        self.assertEqual(cfg.device, "auto")
        self.assertEqual(cfg.data_dir, Path("data/eval_vi"))
        self.assertEqual(cfg.artifacts_dir, Path("docs/generated"))

    def test_sub_configs_are_frozen_instances(self) -> None:
        cfg = MeetingRecapConfig(_env_file=None)
        # Sub-configs are BaseSettings instances and are frozen.
        for sub in (cfg.text_tiling, cfg.chunking,
                    cfg.abstractive, cfg.language):
            self.assertIsInstance(sub, ConfigBase)
            with self.assertRaises(ConfigError):
                sub.window_size = 1  # type: ignore[attr-defined]


class EnvPrefixTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_meeting_recap_prefix_maps_to_nested_field(self) -> None:
        with mock.patch.dict(os.environ, {
            "MEETING_RECAP_CHUNKING__CHUNK_SIZE": "12",
            "MEETING_RECAP_TEXT_TILING__STRIDE": "20",
        }, clear=False):
            cfg = MeetingRecapConfig(_env_file=None)
            self.assertEqual(cfg.chunking.chunk_size, 12)
            self.assertEqual(cfg.text_tiling.stride, 20)

    def test_env_beats_dotenv_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=12\n")
            env_path = f.name
        try:
            with mock.patch.dict(os.environ, {"MEETING_RECAP_CHUNKING__CHUNK_SIZE": "16"}, clear=False):
                cfg = MeetingRecapConfig(_env_file=env_path)
                self.assertEqual(cfg.chunking.chunk_size, 16)
        finally:
            os.unlink(env_path)
            _clear_recap_env()

    def test_dotenv_file_loads_when_no_env_var(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=14\n")
            env_path = f.name
        try:
            cfg = MeetingRecapConfig(_env_file=env_path)
            self.assertEqual(cfg.chunking.chunk_size, 14)
        finally:
            os.unlink(env_path)
            _clear_recap_env()

    def test_env_file_none_skips_file_loading(self) -> None:
        # Even with a stray .env that would override, _env_file=None must skip.
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=99\n")
            env_path = f.name
        try:
            cfg = MeetingRecapConfig(_env_file=None)
            self.assertEqual(cfg.chunking.chunk_size, 8)  # default
        finally:
            os.unlink(env_path)
            _clear_recap_env()

    def test_extra_env_var_ignored_by_default(self) -> None:
        # Pydantic-settings treats unknown env vars as 'ignore' (the
        # underlying model has extra='forbid' for kwarg validation, but
        # the env source does not propagate that to unknown env names).
        # A stricter 'env=forbid' check is deferred -- the current
        # contract is "env vars only set fields that exist; unknown
        # ones are silently ignored", which is also the default for
        # 12-factor config.
        with mock.patch.dict(os.environ, {"MEETING_RECAP_BLOOPER": "1"}, clear=False):
            cfg = MeetingRecapConfig(_env_file=None)
            # No field set, defaults still apply.
            self.assertEqual(cfg.chunking.chunk_size, 8)
            _clear_recap_env()


class ErrorShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_config_error_is_validation_error(self) -> None:
        self.assertTrue(issubclass(ConfigError, pydantic.ValidationError))

    def test_cross_field_rejection_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            MeetingRecapConfig(_env_file=None,
                               text_tiling=TextTilingConfig(window_size=10, stride=20))
        # Pydantic .errors() structure must be preserved
        self.assertTrue(hasattr(ctx.exception, "errors"))
        self.assertIsInstance(ctx.exception.errors(), list)

    def test_data_dir_can_be_overridden(self) -> None:
        cfg = MeetingRecapConfig(_env_file=None, data_dir=Path("/tmp/data"))
        self.assertEqual(cfg.data_dir, Path("/tmp/data"))
