"""Unit tests for HighlightsConfig (paper-2 §3.3, 106 tokens)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.errors import ConfigError
from src.config.highlights import HighlightsConfig


class DefaultsTests(unittest.TestCase):
    def test_paper_anchored_default(self) -> None:
        self.assertEqual(HighlightsConfig().extractive_window, 10)

    def test_frozen(self) -> None:
        cfg = HighlightsConfig()
        with self.assertRaises(ConfigError):
            cfg.extractive_window = 20  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            HighlightsConfig(extractive_window=10, surprise=1)  # type: ignore[call-arg]


class ValidationTests(unittest.TestCase):
    def test_window_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            HighlightsConfig(extractive_window=0)
        with self.assertRaises(ConfigError):
            HighlightsConfig(extractive_window=-1)


class EnvOverrideTests(unittest.TestCase):
    def test_env_var_overrides_window(self) -> None:
        import os
        os.environ["EXTRACTIVE_WINDOW"] = "20"
        try:
            self.assertEqual(HighlightsConfig().extractive_window, 20)
        finally:
            del os.environ["EXTRACTIVE_WINDOW"]
