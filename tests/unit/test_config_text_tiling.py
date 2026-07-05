"""Unit tests for TextTilingConfig (paper-1 Section 3.3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.errors import ConfigError
from src.config.text_tiling import TextTilingConfig


class DefaultsTests(unittest.TestCase):
    def test_paper_anchored_defaults(self) -> None:
        cfg = TextTilingConfig()
        self.assertEqual(cfg.window_size, 30)
        self.assertEqual(cfg.stride, 10)
        self.assertEqual(cfg.smoothing, "mean")
        self.assertEqual(cfg.cutoff_policy, "mean+2std")

    def test_frozen(self) -> None:
        cfg = TextTilingConfig()
        with self.assertRaises(ConfigError):
            cfg.window_size = 40  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            TextTilingConfig(window_size=30, stride=10, smoothing="mean",
                             cutoff_policy="mean+2std", surprise=1)  # type: ignore[call-arg]


class ValidationTests(unittest.TestCase):
    def test_window_size_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            TextTilingConfig(window_size=0, stride=1)

    def test_stride_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            TextTilingConfig(window_size=10, stride=0)

    def test_stride_cannot_exceed_window(self) -> None:
        with self.assertRaises(ConfigError):
            TextTilingConfig(window_size=10, stride=20)

    def test_invalid_smoothing_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            TextTilingConfig(window_size=10, stride=5, smoothing="bogus")

    def test_invalid_cutoff_policy_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            TextTilingConfig(window_size=10, stride=5, cutoff_policy="bogus")


class EnvOverrideTests(unittest.TestCase):
    def test_env_var_overrides_field(self) -> None:
        # Sub-configs (e.g. TextTilingConfig) have no env_prefix and no
        # env_nested_delimiter: the env-var name is the bare field name.
        # The nested-delimiter behaviour only kicks in inside
        # MeetingRecapConfig (which composes the sub-configs).
        import os
        os.environ["WINDOW_SIZE"] = "45"
        os.environ["STRIDE"] = "15"
        try:
            cfg = TextTilingConfig()
            self.assertEqual(cfg.window_size, 45)
            self.assertEqual(cfg.stride, 15)
        finally:
            del os.environ["WINDOW_SIZE"]
            del os.environ["STRIDE"]
