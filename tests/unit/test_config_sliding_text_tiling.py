"""Unit tests for SlidingTextTilingConfig."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.errors import ConfigError
from src.config.text_tiling import SlidingTextTilingConfig


class DefaultsTests(unittest.TestCase):
    def test_defaults_match_reference_implementation(self) -> None:
        cfg = SlidingTextTilingConfig()
        self.assertEqual(cfg.block_size, 3)
        self.assertEqual(cfg.radii, [3, 5, 10, 15, 20])
        self.assertEqual(cfg.alpha, 0.9)
        self.assertEqual(cfg.use_stopwords, True)
        self.assertEqual(cfg.agg, "mean")
        self.assertEqual(cfg.normalize, "zscore")
        self.assertEqual(cfg.min_segment_ratio, 0.08)

    def test_frozen(self) -> None:
        cfg = SlidingTextTilingConfig()
        with self.assertRaises(ConfigError):
            cfg.block_size = 5  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            SlidingTextTilingConfig(
                block_size=3,
                radii=[3, 5, 10],
                alpha=0.9,
                use_stopwords=True,
                agg="mean",
                normalize="zscore",
                min_segment_ratio=0.08,
                surprise=1,  # type: ignore[call-arg]
            )


class ValidationTests(unittest.TestCase):
    def test_block_size_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            SlidingTextTilingConfig(block_size=0)

    def test_radii_must_be_non_empty(self) -> None:
        with self.assertRaises(ConfigError):
            SlidingTextTilingConfig(radii=[])

    def test_radii_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            SlidingTextTilingConfig(radii=[0])

    def test_invalid_agg_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            SlidingTextTilingConfig(agg="bogus")  # type: ignore[arg-type]

    def test_invalid_normalize_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            SlidingTextTilingConfig(normalize="bogus")  # type: ignore[arg-type]

    def test_min_segment_ratio_out_of_range(self) -> None:
        with self.assertRaises(ConfigError):
            SlidingTextTilingConfig(min_segment_ratio=1.5)

    def test_custom_radii_accepted(self) -> None:
        cfg = SlidingTextTilingConfig(radii=[5, 10, 15])
        self.assertEqual(cfg.radii, [5, 10, 15])

    def test_custom_alpha_accepted(self) -> None:
        cfg = SlidingTextTilingConfig(alpha=1.5)
        self.assertEqual(cfg.alpha, 1.5)


class EnvOverrideTests(unittest.TestCase):
    def test_env_var_overrides_field(self) -> None:
        # Sub-configs have no env_prefix — bare field names match env vars.
        import os
        os.environ["BLOCK_SIZE"] = "5"
        os.environ["ALPHA"] = "1.2"
        try:
            cfg = SlidingTextTilingConfig()
            self.assertEqual(cfg.block_size, 5)
            self.assertEqual(cfg.alpha, 1.2)
        finally:
            del os.environ["BLOCK_SIZE"]
            del os.environ["ALPHA"]