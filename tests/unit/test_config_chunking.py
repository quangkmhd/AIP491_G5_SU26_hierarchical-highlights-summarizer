"""Unit tests for ChunkingConfig (paper-2 §3.3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.chunking import ChunkingConfig
from src.config.errors import ConfigError


class DefaultsTests(unittest.TestCase):
    def test_paper_anchored_defaults(self) -> None:
        cfg = ChunkingConfig()
        self.assertEqual(cfg.chunk_size, 8)
        self.assertEqual(cfg.overlap, 0)

    def test_frozen(self) -> None:
        cfg = ChunkingConfig()
        with self.assertRaises(ConfigError):
            cfg.chunk_size = 16  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            ChunkingConfig(chunk_size=8, overlap=0, surprise=1)  # type: ignore[call-arg]


class ValidationTests(unittest.TestCase):
    def test_chunk_size_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            ChunkingConfig(chunk_size=0)

    def test_overlap_must_be_non_negative(self) -> None:
        with self.assertRaises(ConfigError):
            ChunkingConfig(chunk_size=8, overlap=-1)

    def test_overlap_must_be_strictly_less_than_chunk_size(self) -> None:
        with self.assertRaises(ConfigError):
            ChunkingConfig(chunk_size=8, overlap=8)
        with self.assertRaises(ConfigError):
            ChunkingConfig(chunk_size=8, overlap=10)

    def test_overlap_equal_to_chunk_size_minus_one_allowed(self) -> None:
        cfg = ChunkingConfig(chunk_size=8, overlap=7)
        self.assertEqual(cfg.overlap, 7)


class EnvOverrideTests(unittest.TestCase):
    def test_env_var_overrides_chunk_size(self) -> None:
        import os
        os.environ["CHUNK_SIZE"] = "12"
        try:
            self.assertEqual(ChunkingConfig().chunk_size, 12)
        finally:
            del os.environ["CHUNK_SIZE"]
