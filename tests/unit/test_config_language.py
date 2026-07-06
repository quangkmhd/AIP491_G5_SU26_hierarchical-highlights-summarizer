"""Unit tests for LanguageConfig (paper-1 §3 + vi extension)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.errors import ConfigError
from src.config.language import LanguageConfig


class DefaultsTests(unittest.TestCase):
    def test_vietnamese_default(self) -> None:
        cfg = LanguageConfig()
        self.assertEqual(cfg.tag, "vi")
        self.assertEqual(cfg.model_variant, "FPTAI/vibert-base-cased")

    def test_frozen(self) -> None:
        cfg = LanguageConfig()
        with self.assertRaises(ConfigError):
            cfg.tag = "en"  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="vi", model_variant="FPTAI/vibert-base-cased",
                           surprise=1)  # type: ignore[call-arg]


class ValidationTests(unittest.TestCase):
    def test_zh_requires_chinese_variant(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="zh", model_variant="FPTAI/vibert-base-cased")

    def test_en_requires_non_chinese_variant(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="en", model_variant="bert-base-chinese")

    def test_vi_requires_non_chinese_variant(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="vi", model_variant="bert-base-chinese")

    def test_valid_combinations_accepted(self) -> None:
        LanguageConfig(tag="vi", model_variant="FPTAI/vibert-base-cased")
        LanguageConfig(tag="en", model_variant="bert-base-multilingual-cased")
        LanguageConfig(tag="zh", model_variant="bert-base-chinese")


class EnvOverrideTests(unittest.TestCase):
    def test_env_var_overrides_tag(self) -> None:
        import os
        os.environ["TAG"] = "en"
        try:
            self.assertEqual(LanguageConfig().tag, "en")
        finally:
            del os.environ["TAG"]
