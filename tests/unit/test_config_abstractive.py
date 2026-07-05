"""Unit tests for AbstractiveConfig (paper-2 §3.3, 512 tokens)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.abstractive import AbstractiveConfig
from src.config.errors import ConfigError


class DefaultsTests(unittest.TestCase):
    def test_paper_anchored_default(self) -> None:
        self.assertEqual(AbstractiveConfig().context_window, 512)

    def test_frozen(self) -> None:
        cfg = AbstractiveConfig()
        with self.assertRaises(ConfigError):
            cfg.context_window = 1024  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            AbstractiveConfig(context_window=512, surprise=1)  # type: ignore[call-arg]


class ValidationTests(unittest.TestCase):
    def test_window_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            AbstractiveConfig(context_window=0)
