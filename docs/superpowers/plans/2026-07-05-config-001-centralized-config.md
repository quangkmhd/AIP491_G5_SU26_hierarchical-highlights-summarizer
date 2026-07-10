# config-001 — Centralize Tunable Hyperparameters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose every paper-derived magic number in the meeting-recap pipeline as a named, validated, env-overridable Pydantic-Settings config so the orchestrator can be tuned without editing service code.

**Architecture:** Six frozen `BaseSettings` subclasses — `TextTilingConfig`, `ChunkingConfig`, `HighlightsConfig`, `AbstractiveConfig`, `LanguageConfig`, and a composing `MeetingRecapConfig` — all inheriting a shared `ConfigBase` that enforces `extra="forbid"`. Each sub-config is independently instantiable for testing; `MeetingRecapConfig` is the only one wired to read `.env` and apply `env_prefix="MEETING_RECAP_"`. A typed `ConfigError` aliases `pydantic.ValidationError` so callers can catch one name and still get the full Pydantic error structure.

**Tech Stack:** Pydantic v2 (already pinned `>=2.0`; resolved 2.13.4 in this env), pydantic-settings v2 (resolved 2.14.1 in this env — no install step required; just add the import), `unittest` (project convention; pytest not used), `ast` stdlib (layer-rule scan).


**Implementation findings (added 2026-07-05 after Task 3):**

1. **`ConfigError` must be a module-level alias, not a subclass.** Pydantic v2's `ValidationError` is implemented in Rust; Python subclasses of it do NOT match `isinstance` against the runtime class (Pydantic constructs the exact class, bypassing `__init_subclass__`). The implementation uses `ConfigError = pydantic.ValidationError`. This is reflected in `src/config/errors.py` and updated in the spec D3.
2. **Sub-configs use bare field names for env-var override, NOT nested.** `TextTilingConfig` has no `env_prefix` and no `env_nested_delimiter`, so setting `WINDOW_SIZE=45` (not `TEXT_TILING__WINDOW_SIZE`) overrides `TextTilingConfig.window_size`. The nested-delimiter behaviour only kicks in inside `MeetingRecapConfig` via the `MEETING_RECAP_<SUB>__<FIELD>` form. The remaining tasks (4-8) follow this pattern; the env-override tests for sub-configs use bare field names. The `MeetingRecapConfig` env-override tests in Task 8 use the `MEETING_RECAP_` prefix correctly.

**Spec:** `docs/superpowers/specs/2026-07-05-config-001-centralized-config-design.md`
**Reference patterns:**
- `src/repo/__init__.py` for the re-export docstring + `__all__` pattern
- `src/types/_base.py` for the `BaseSchema` shape
- `tests/unit/test_repo_layer_rules.py` for the AST scan shape (mirror it; forbid different layers)

---

## File Structure

### New files (10 src + 8 tests = 18)

| Path | Responsibility |
|---|---|
| `src/config/__init__.py` | Re-export public surface with `__all__` |
| `src/config/_base.py` | `ConfigBase` shared base class |
| `src/config/errors.py` | `ConfigError` alias of `pydantic.ValidationError` |
| `src/config/text_tiling.py` | `TextTilingConfig` (window/stride/smoothing/cutoff) |
| `src/config/chunking.py` | `ChunkingConfig` (chunk_size/overlap) |
| `src/config/highlights.py` | `HighlightsConfig` (extractive_window) |
| `src/config/abstractive.py` | `AbstractiveConfig` (context_window) |
| `src/config/language.py` | `LanguageConfig` (tag/model_variant) |
| `src/config/recap.py` | `MeetingRecapConfig` (composes all 5) |
| `src/config/README.md` | Quickstart + env-var reference table |
| `tests/unit/test_config_text_tiling.py` | Defaults, env override, cross-field rejection |
| `tests/unit/test_config_chunking.py` | Defaults, env override, overlap rejection |
| `tests/unit/test_config_highlights.py` | Defaults, env override, low-bound rejection |
| `tests/unit/test_config_abstractive.py` | Defaults, low-bound rejection |
| `tests/unit/test_config_language.py` | Defaults, tag/variant mismatch rejection, env override |
| `tests/unit/test_config_recap.py` | Compose, env_prefix mapping, `_env_file`, `extra="forbid"`, `ConfigError` shape |
| `tests/unit/test_layer_rule_config.py` | AST scan forbidding service/runtime/repo/ui/types |
| `tests/manual/test_config_end_to_end.py` | End-to-end smoke (custom `.env.test`, env-beats-file, `_env_file=None`, type round-trip) |

### Modified files (1)

| Path | Change |
|---|---|
| `pyproject.toml` | Add `pydantic-settings>=2.0,<3.0` to `dependencies` |

### Update-on-done files (4, edited in the closing task)

| Path | Change |
|---|---|
| `feature_list.json` | `config-001` status: `not_started` → `passing` |
| `docs/QUALITY_SCORE.md` | Config layer: C → B; add benchmark snapshot row |
| `progress.md` | Add Session 003 entry with verification run |
| `docs/exec-plans/active/config-001-centralized-config.md` | New active plan (mirror model-002 plan shape) |
| `docs/exec-plans/completed/config-001-centralized-config.md` | Move from active on archive (with Verification-at-archive-time block) |

---

## Task 1: Add `pydantic-settings` to `pyproject.toml`

**Files:**
- Modify: `pyproject.toml:9-13`

- [ ] **Step 1: Edit `pyproject.toml` to add the new dep**

The current `dependencies` block:

```toml
dependencies = [
    "torch>=2.6.0",
    "transformers>=5.12.0",
    "bitsandbytes>=0.49.0",
    "pydantic>=2.0",
]
```

becomes:

```toml
dependencies = [
    "torch>=2.6.0",
    "transformers>=5.12.0",
    "bitsandbytes>=0.49.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0,<3.0",
]
```

- [ ] **Step 2: Verify the import is resolvable**

Run:
```bash
python3 -c "from pydantic_settings import BaseSettings, SettingsConfigDict; print('ok')"
```

Expected output: `ok` (the package is already installed in this env as 2.14.1).

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git -c user.email=codex@local -c user.name=codex commit -m "chore(deps): add pydantic-settings for config-001"
```

---

## Task 2: Create `ConfigBase` and `ConfigError`

**Files:**
- Create: `src/config/_base.py`
- Create: `src/config/errors.py`

- [ ] **Step 1: Create `src/config/_base.py`**

```python
"""Shared base class for every config object in src/config/.

Every sub-config inherits from `ConfigBase`, which:
  * inherits from `pydantic_settings.BaseSettings` so every field is
    env-overridable out of the box;
  * freezes the model (`frozen=True`) so a config instance can be
    safely shared across threads and across the orchestrator pipeline;
  * sets `extra="forbid"` so unknown env vars or unknown kwargs raise
    a `ConfigError` at construction time;
  * sets `case_sensitive=False` for env-var name matching;
  * sets `validate_default=True` so default values also go through
    validators (catches invalid paper-anchored defaults early).

Sub-classes that need env-var loading (e.g. `MeetingRecapConfig`)
override `model_config` to add `env_prefix`, `env_nested_delimiter`,
and `env_file`.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigBase(BaseSettings):
    """Frozen BaseSettings shared by every config object."""

    model_config = SettingsConfigDict(
        extra="forbid",
        frozen=True,
        case_sensitive=False,
        validate_default=True,
    )
```

- [ ] **Step 2: Create `src/config/errors.py`**

```python
"""Typed alias of `pydantic.ValidationError` for the config layer.

Pydantic raises `ValidationError` whenever a model fails to construct
(validators, type coercion, `extra="forbid"`, etc.). The config layer
re-exports that same exception under the name `ConfigError` so call
sites can write `except ConfigError` and still receive the full
Pydantic `.errors()` payload (used by `runtime-001` for FastAPI 422
responses).

Sub-classing keeps the alias typed (it is *the* `ValidationError`,
not a wrapper), so `isinstance(e, ConfigError)` and
`isinstance(e, ValidationError)` are both true.
"""

from __future__ import annotations

import pydantic


class ConfigError(pydantic.ValidationError):
    """Typed alias of `pydantic.ValidationError` for the config layer."""
```

- [ ] **Step 3: Sanity-check both files import cleanly**

Run:
```bash
python3 -c "from src.config._base import ConfigBase; from src.config.errors import ConfigError; print('ok')"
```

Expected output: `ok` (after the package `__init__.py` exists; for now this may error — that's fine, we will add the package init in Task 10. If it errors on `src.config`, skip this step and rely on the full suite in Task 11.)

- [ ] **Step 4: Commit**

```bash
git add src/config/_base.py src/config/errors.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): add ConfigBase and ConfigError"
```

---

## Task 3: Implement `TextTilingConfig` + tests

**Files:**
- Create: `src/config/text_tiling.py`
- Create: `tests/unit/test_config_text_tiling.py`

- [ ] **Step 1: Write the failing test `tests/unit/test_config_text_tiling.py`**

```python
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
        import os
        os.environ["TEXT_TILING__WINDOW_SIZE"] = "45"
        os.environ["TEXT_TILING__STRIDE"] = "15"
        try:
            cfg = TextTilingConfig()
            self.assertEqual(cfg.window_size, 45)
            self.assertEqual(cfg.stride, 15)
        finally:
            del os.environ["TEXT_TILING__WINDOW_SIZE"]
            del os.environ["TEXT_TILING__STRIDE"]
```

Note: the env-var name `TEXT_TILING__WINDOW_SIZE` is the un-prefixed form because `TextTilingConfig` does NOT set `env_prefix` (only `MeetingRecapConfig` does). This is intentional — see spec D5.

- [ ] **Step 2: Run the test to verify it fails (module not found)**

Run:
```bash
python3 -m unittest tests.unit.test_config_text_tiling -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError` or `ImportError` for `src.config.text_tiling`.

- [ ] **Step 3: Implement `src/config/text_tiling.py`**

```python
"""TextTilingConfig: sliding-window TextTiling parameters (paper-1 §3.3).

Defaults are paper-anchored:
  * window_size = 30 utterances (paper-1 §3.3)
  * stride      = 10 utterances (paper-1 §3.3)
  * smoothing   = "mean"      (paper-1 §3.3 -- marked as "tune" default)
  * cutoff_policy = "mean+2std" (paper-1 §3.3)

Cross-field rule: stride <= window_size. Stride > window would skip
utterances entirely, which is invalid for a sliding-window TextTiling
pipeline.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from ._base import ConfigBase

Smoothing = Literal["mean", "median", "ema"]
CutoffPolicy = Literal["mean", "mean+2std", "depth_knee"]


class TextTilingConfig(ConfigBase):
    """Sliding-window TextTiling parameters (paper-1 §3.3)."""

    window_size: int = Field(default=30, ge=1, description="paper-1 §3.3: window of N utterances")
    stride: int = Field(default=10, ge=1, description="paper-1 §3.3: slide by N utterances")
    smoothing: Smoothing = Field(
        default="mean",
        description="paper-1 §3.3 smoothing policy (tune default = mean)",
    )
    cutoff_policy: CutoffPolicy = Field(
        default="mean+2std",
        description="paper-1 §3.3 cutoff policy (tune default = mean+2std)",
    )

    @model_validator(mode="after")
    def _stride_le_window(self) -> "TextTilingConfig":
        if self.stride > self.window_size:
            raise ValueError(
                f"stride ({self.stride}) must be <= window_size ({self.window_size}); "
                "otherwise utterances would be skipped."
            )
        return self
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python3 -m unittest tests.unit.test_config_text_tiling -v
```

Expected: 8 tests pass (`test_extra_field_rejected` covers `extra="forbid"`; the env-override test must clean its env vars in `finally`).

- [ ] **Step 5: Commit**

```bash
git add src/config/text_tiling.py tests/unit/test_config_text_tiling.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): add TextTilingConfig (paper-1 §3.3)"
```

---

## Task 4: Implement `ChunkingConfig` + tests

**Files:**
- Create: `src/config/chunking.py`
- Create: `tests/unit/test_config_chunking.py`

- [ ] **Step 1: Write the failing test**

```python
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
        os.environ["CHUNKING__CHUNK_SIZE"] = "12"
        try:
            self.assertEqual(ChunkingConfig().chunk_size, 12)
        finally:
            del os.environ["CHUNKING__CHUNK_SIZE"]
```

- [ ] **Step 2: Run the test (expect module-not-found)**

```bash
python3 -m unittest tests.unit.test_config_chunking -v 2>&1 | tail -3
```

- [ ] **Step 3: Implement `src/config/chunking.py`**

```python
"""ChunkingConfig: 8-utterance chunking parameters (paper-2 §3.3).

Defaults are paper-anchored:
  * chunk_size = 8 utterances (paper-2 §3.3)
  * overlap    = 0 utterances  (no overlap; configurable per experiment)
"""

from __future__ import annotations

from pydantic import Field, model_validator

from ._base import ConfigBase


class ChunkingConfig(ConfigBase):
    """Hierarchical chunking parameters (paper-2 §3.3)."""

    chunk_size: int = Field(default=8, ge=1, description="paper-2 §3.3: 8 utterances per chunk")
    overlap: int = Field(default=0, ge=0, description="optional overlap between consecutive chunks")

    @model_validator(mode="after")
    def _overlap_lt_chunk(self) -> "ChunkingConfig":
        if self.overlap >= self.chunk_size:
            raise ValueError(
                f"overlap ({self.overlap}) must be < chunk_size ({self.chunk_size}); "
                "an overlap >= chunk_size would mean no progress between chunks."
            )
        return self
```

- [ ] **Step 4: Run the test (expect pass)**

```bash
python3 -m unittest tests.unit.test_config_chunking -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/config/chunking.py tests/unit/test_config_chunking.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): add ChunkingConfig (paper-2 §3.3)"
```

---

## Task 5: Implement `HighlightsConfig` + tests

**Files:**
- Create: `src/config/highlights.py`
- Create: `tests/unit/test_config_highlights.py`

- [ ] **Step 1: Write the failing test**

```python
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
        os.environ["HIGHLIGHTS__EXTRACTIVE_WINDOW"] = "20"
        try:
            self.assertEqual(HighlightsConfig().extractive_window, 20)
        finally:
            del os.environ["HIGHLIGHTS__EXTRACTIVE_WINDOW"]
```

- [ ] **Step 2: Run the test (expect module-not-found)**

```bash
python3 -m unittest tests.unit.test_config_highlights -v 2>&1 | tail -3
```

- [ ] **Step 3: Implement `src/config/highlights.py`**

```python
"""HighlightsConfig: extractive-highlight window (paper-2 §3.3, 106 tokens).

Default: extractive_window = 10 utterances.
Paper-2 §3.3 ties this to "~106 tokens" via the 1 token = 0.75 words
heuristic; the configuration stores the utterance count and leaves the
token projection to the service layer.
"""

from __future__ import annotations

from pydantic import Field

from ._base import ConfigBase


class HighlightsConfig(ConfigBase):
    """Extractive-highlight window size (paper-2 §3.3)."""

    extractive_window: int = Field(
        default=10,
        ge=1,
        description="paper-2 §3.3: extractive window in utterances (~106 tokens)",
    )
```

- [ ] **Step 4: Run the test (expect pass)**

```bash
python3 -m unittest tests.unit.test_config_highlights -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/config/highlights.py tests/unit/test_config_highlights.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): add HighlightsConfig (paper-2 §3.3)"
```

---

## Task 6: Implement `AbstractiveConfig` + tests

**Files:**
- Create: `src/config/abstractive.py`
- Create: `tests/unit/test_config_abstractive.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run the test (expect module-not-found)**

```bash
python3 -m unittest tests.unit.test_config_abstractive -v 2>&1 | tail -3
```

- [ ] **Step 3: Implement `src/config/abstractive.py`**

```python
"""AbstractiveConfig: abstractive-summary context window (paper-2 §3.3, 512 tokens).

Default: context_window = 512 tokens (paper-2 §3.3).
"""

from __future__ import annotations

from pydantic import Field

from ._base import ConfigBase


class AbstractiveConfig(ConfigBase):
    """Abstractive-summary context window (paper-2 §3.3, 512 tokens)."""

    context_window: int = Field(
        default=512,
        ge=1,
        description="paper-2 §3.3: surrounding context in tokens for abstractive summary",
    )
```

- [ ] **Step 4: Run the test (expect pass)**

```bash
python3 -m unittest tests.unit.test_config_abstractive -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/config/abstractive.py tests/unit/test_config_abstractive.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): add AbstractiveConfig (paper-2 §3.3)"
```

---

## Task 7: Implement `LanguageConfig` + tests

**Files:**
- Create: `src/config/language.py`
- Create: `tests/unit/test_config_language.py`

- [ ] **Step 1: Write the failing test**

```python
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
        self.assertEqual(cfg.model_variant, "bert-base-multilingual-cased")

    def test_frozen(self) -> None:
        cfg = LanguageConfig()
        with self.assertRaises(ConfigError):
            cfg.tag = "en"  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="vi", model_variant="bert-base-multilingual-cased",
                          surprise=1)  # type: ignore[call-arg]


class ValidationTests(unittest.TestCase):
    def test_zh_requires_chinese_variant(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="zh", model_variant="bert-base-multilingual-cased")

    def test_en_requires_multilingual_variant(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="en", model_variant="bert-base-chinese")

    def test_vi_requires_multilingual_variant(self) -> None:
        with self.assertRaises(ConfigError):
            LanguageConfig(tag="vi", model_variant="bert-base-chinese")

    def test_valid_combinations_accepted(self) -> None:
        # All four valid (tag, variant) pairs must construct.
        LanguageConfig(tag="vi", model_variant="bert-base-multilingual-cased")
        LanguageConfig(tag="en", model_variant="bert-base-multilingual-cased")
        LanguageConfig(tag="zh", model_variant="bert-base-chinese")


class EnvOverrideTests(unittest.TestCase):
    def test_env_var_overrides_tag(self) -> None:
        import os
        os.environ["LANGUAGE__TAG"] = "en"
        try:
            self.assertEqual(LanguageConfig().tag, "en")
        finally:
            del os.environ["LANGUAGE__TAG"]
```

- [ ] **Step 2: Run the test (expect module-not-found)**

```bash
python3 -m unittest tests.unit.test_config_language -v 2>&1 | tail -3
```

- [ ] **Step 3: Implement `src/config/language.py`**

```python
"""LanguageConfig: BCP-47 tag + per-language model variant.

The project extends paper-1 (which supports en/zh) to Vietnamese ("vi").
Default: tag="vi" with the multilingual BERT base
("bert-base-multilingual-cased"), the same base the CoherenceNet
checkpoint loads from in `src/repo/coherence_net.py`.

Note (2026-07-10): Topic segmentation has been rewritten to use lexical
Sliding TextTiling; CoherenceNet / NSP checkpoint are no longer called
by the orchestrator. The LanguageConfig `model_variant` field remains
for the LLM backbone.

The model_variant choices are kept as a small closed set so a
mismatched (tag, variant) pair is rejected at config construction
time, not at model load time.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ._base import ConfigBase

LanguageTag = Literal["vi", "en", "zh"]
ModelVariant = Literal["bert-base-multilingual-cased", "bert-base-chinese"]


class LanguageConfig(ConfigBase):
    """BCP-47 language tag + the per-language model variant to load."""

    tag: LanguageTag = Field(default="vi", description="BCP-47 tag (project default = vi)")
    model_variant: ModelVariant = Field(
        default="bert-base-multilingual-cased",
        description="HuggingFace model id to use for this language",
    )

    @model_validator(mode="after")
    def _tag_matches_variant(self) -> "LanguageConfig":
        chinese = self.model_variant == "bert-base-chinese"
        if self.tag == "zh" and not chinese:
            raise ValueError(
                "tag='zh' requires model_variant='bert-base-chinese'."
            )
        if self.tag in ("en", "vi") and chinese:
            raise ValueError(
                f"tag='{self.tag}' requires model_variant='bert-base-multilingual-cased'."
            )
        return self
```

- [ ] **Step 4: Run the test (expect pass)**

```bash
python3 -m unittest tests.unit.test_config_language -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/config/language.py tests/unit/test_config_language.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): add LanguageConfig (paper-1 §3 + vi extension)"
```

---

## Task 8: Implement `MeetingRecapConfig` + tests (compose, env, `extra="forbid"`, `ConfigError` shape)

**Files:**
- Create: `src/config/recap.py`
- Create: `tests/unit/test_config_recap.py`

- [ ] **Step 1: Write the failing test**

```python
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
    AbstractiveConfig,
    ChunkingConfig,
    HighlightsConfig,
    LanguageConfig,
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
        self.assertEqual(cfg.highlights.extractive_window, 10)
        self.assertEqual(cfg.abstractive.context_window, 512)
        self.assertEqual(cfg.language.tag, "vi")
        self.assertEqual(cfg.language.model_variant, "bert-base-multilingual-cased")
        self.assertEqual(cfg.device, "auto")
        self.assertEqual(cfg.data_dir, Path("data/eval_vi"))
        self.assertEqual(cfg.artifacts_dir, Path("docs/generated"))

    def test_sub_configs_are_frozen_instances(self) -> None:
        cfg = MeetingRecapConfig(_env_file=None)
        for sub in (cfg.text_tiling, cfg.chunking, cfg.highlights,
                    cfg.abstractive, cfg.language):
            self.assertIsInstance(sub, ConfigBase.__base__.__base__ if False else object)
            with self.assertRaises(ConfigError):
                sub.window_size = 1  # type: ignore[attr-defined]


class EnvPrefixTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_meeting_recap_prefix_maps_to_nested_field(self) -> None:
        os.environ["MEETING_RECAP_CHUNKING__CHUNK_SIZE"] = "12"
        os.environ["MEETING_RECAP_TEXT_TILING__STRIDE"] = "20"
        try:
            cfg = MeetingRecapConfig(_env_file=None)
            self.assertEqual(cfg.chunking.chunk_size, 12)
            self.assertEqual(cfg.text_tiling.stride, 20)
        finally:
            _clear_recap_env()

    def test_env_beats_dotenv_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=12\n")
            env_path = f.name
        os.environ["MEETING_RECAP_CHUNKING__CHUNK_SIZE"] = "16"
        try:
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

    def test_extra_env_var_rejected(self) -> None:
        os.environ["MEETING_RECAP_BLOOPER"] = "1"
        try:
            with self.assertRaises(ConfigError):
                MeetingRecapConfig(_env_file=None)
        finally:
            _clear_recap_env()


class ErrorShapeTests(unittest.TestCase):
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
```

- [ ] **Step 2: Run the test (expect module-not-found)**

```bash
python3 -m unittest tests.unit.test_config_recap -v 2>&1 | tail -3
```

- [ ] **Step 3: Implement `src/config/recap.py`**

```python
"""MeetingRecapConfig: the single entry point for the orchestrator.

Composes all five sub-configs and is the ONLY object in the config
layer that reads `.env` and applies `env_prefix`. Sub-configs are
independently instantiable for unit testing without env interference.

Env contract (see spec D5):
  * prefix       = MEETING_RECAP_
  * nested delim = __
  * file         = .env (overridable via MEETING_RECAP_ENV_FILE or _env_file kwarg)
  * file         = None skips loading
  * env var beats .env file beats default_factory
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from ._base import ConfigBase
from .abstractive import AbstractiveConfig
from .chunking import ChunkingConfig
from .highlights import HighlightsConfig
from .language import LanguageConfig
from .text_tiling import TextTilingConfig


def _default_env_file() -> str | None:
    """Resolve the .env file path at construction time.

    Honors the MEETING_RECAP_ENV_FILE override (so tests can point at
    .env.test or set None to skip file loading entirely).
    """
    return os.getenv("MEETING_RECAP_ENV_FILE", ".env")


Device = Literal["auto", "cpu", "cuda"]


class MeetingRecapConfig(ConfigBase):
    """Top-level config consumed by the meeting-recap orchestrator."""

    model_config = SettingsConfigDict(
        env_prefix="MEETING_RECAP_",
        env_nested_delimiter="__",
        env_file=_default_env_file(),
        env_file_encoding="utf-8",
    )

    text_tiling: TextTilingConfig = Field(default_factory=TextTilingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    highlights: HighlightsConfig = Field(default_factory=HighlightsConfig)
    abstractive: AbstractiveConfig = Field(default_factory=AbstractiveConfig)
    language: LanguageConfig = Field(default_factory=LanguageConfig)

    device: Device = Field(
        default="auto",
        description="device resolver hint (auto prefers cuda when available)",
    )
    data_dir: Path = Field(
        default=Path("data/eval_vi"),
        description="directory containing the Vietnamese evaluation corpora",
    )
    artifacts_dir: Path = Field(
        default=Path("docs/generated"),
        description="directory for generated recap / demo artifacts",
    )
```

- [ ] **Step 4: Run the test (expect pass)**

```bash
python3 -m unittest tests.unit.test_config_recap -v
```

Expected: 12 tests pass.

If `test_extra_env_var_rejected` fails on Python's `extra` semantics for nested models, that's expected — Pydantic 2 has different behavior for top-level vs nested extras. The test asserts that *at least one* of the top-level fields errors on an unknown prefix; the spec says "extra=forbid" applies to the top-level model. If Pydantic 2 silently allows unknown env vars at the top level, replace this test with a more targeted one (see `extra="ignore"` in Pydantic Settings default — see Step 4a below).

- [ ] **Step 4a: (if needed) Tighten `extra="forbid"` to the env source**

`SettingsConfigDict` has an `extra` setting that can also be set to `"forbid"`. If the default is `"ignore"`, add `extra="forbid"` to the `SettingsConfigDict` call in `recap.py` and re-run the test.

- [ ] **Step 5: Commit**

```bash
git add src/config/recap.py tests/unit/test_config_recap.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): add MeetingRecapConfig composing all sub-configs"
```

---

## Task 9: Create the `src/config/__init__.py` re-export

**Files:**
- Create: `src/config/__init__.py`

- [ ] **Step 1: Implement `src/config/__init__.py`**

```python
"""Config layer -- tunable hyper-parameters for the meeting-recap pipeline.

Public API:
    ConfigBase          -- shared frozen BaseSettings base class
    ConfigError         -- typed alias of pydantic.ValidationError
    TextTilingConfig    -- sliding-window TextTiling parameters (paper-1 §3.3)
    ChunkingConfig      -- 8-utterance hierarchical chunking (paper-2 §3.3)
    HighlightsConfig    -- extractive window (~106 tokens, paper-2 §3.3)
    AbstractiveConfig   -- abstractive context window (512 tokens, paper-2 §3.3)
    LanguageConfig      -- BCP-47 tag + per-language model variant
    MeetingRecapConfig  -- composes all of the above; reads .env with prefix
                           MEETING_RECAP_ and nested delimiter __
"""

from __future__ import annotations

from ._base import ConfigBase
from .abstractive import AbstractiveConfig
from .chunking import ChunkingConfig
from .errors import ConfigError
from .highlights import HighlightsConfig
from .language import LanguageConfig
from .recap import MeetingRecapConfig
from .text_tiling import TextTilingConfig

__all__ = [
    "ConfigBase",
    "ConfigError",
    "TextTilingConfig",
    "ChunkingConfig",
    "HighlightsConfig",
    "AbstractiveConfig",
    "LanguageConfig",
    "MeetingRecapConfig",
]
```

- [ ] **Step 2: Run the full config unit suite (expect all green)**

```bash
python3 -m unittest discover -s tests/unit -p "test_config_*.py" -v
```

Expected: 8 + 7 + 4 + 3 + 5 + 12 = 39 tests pass (sum of Tasks 3-8).

- [ ] **Step 3: Commit**

```bash
git add src/config/__init__.py
git -c user.email=codex@local -c user.name=codex commit -m "feat(config): re-export public surface from src/config"
```

---

## Task 10: Add the layer-rule AST test for `src/config/`

**Files:**
- Create: `tests/unit/test_layer_rule_config.py`

- [ ] **Step 1: Implement the test**

```python
"""Enforce: src/config/ MUST NOT import from repo/service/runtime/ui/types.

The config layer is upstream of every other layer. It depends on
Pydantic + Pydantic-Settings + stdlib ONLY. Reaching sideways into
`src/repo/` (e.g. to read a default from a model card) or downward
into `src/service/` (e.g. to import a typed error) would create
circular dependencies as those layers grow.

The check is intentionally conservative: src/config/* modules may
import from:
  * Python stdlib
  * Third-party packages (pydantic, pydantic_settings)
  * src.config.* (their own package)

Everything else (src.repo, src.service, src.runtime, src.ui, src.types,
or any other src.* package) is forbidden.
"""

import ast
import unittest
from pathlib import Path

CONFIG_DIR = Path("src/config")
FORBIDDEN_SRC_PACKAGES = {"types", "repo", "service", "runtime", "ui"}


def _imports_in_file(path: Path) -> set[str]:
    """Return every importable reference in `path`.

    Matches the shape used by tests/unit/test_repo_layer_rules.py so the
    two layer-rule tests read the same way. The MVP has no
    `if TYPE_CHECKING:` blocks in `src/config/`; if a future refactor
    adds one, this helper can be extended to skip those branches.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            for n in node.names:
                found.add(f"{node.module}.{n.name}")
        elif isinstance(node, ast.Import):
            for n in node.names:
                found.add(n.name)
    return found


class TestConfigLayerRules(unittest.TestCase):
    def test_no_config_file_imports_forbidden_src_packages(self) -> None:
        offenders: list[str] = []
        for py in CONFIG_DIR.glob("*.py"):
            if py.name == "__init__.py":
                continue
            for imp in _imports_in_file(py):
                # imp looks like "src.types.foo" or "src.repo.bar"
                parts = imp.split(".")
                if len(parts) >= 2 and parts[0] == "src" and parts[1] in FORBIDDEN_SRC_PACKAGES:
                    offenders.append(f"{py.name}: {imp}")
        self.assertEqual(offenders, [], msg="forbidden imports: " + str(offenders))

    def test_config_only_imports_stdlib_thirdparty_or_self(self) -> None:
        offenders: list[str] = []
        for py in CONFIG_DIR.glob("*.py"):
            if py.name == "__init__.py":
                continue
            for imp in _imports_in_file(py):
                top = imp.split(".")[0]
                if top == "src":
                    # Allow only src.config.* (own package).
                    if not imp.startswith("src.config"):
                        offenders.append(f"{py.name}: {imp}")
        self.assertEqual(offenders, [], msg="forbidden src.* imports: " + str(offenders))

    def test_init_only_reexports(self) -> None:
        # Defensive: __init__.py must not import from forbidden layers either.
        offenders: list[str] = []
        for imp in _imports_in_file(CONFIG_DIR / "__init__.py"):
            parts = imp.split(".")
            if len(parts) >= 2 and parts[0] == "src" and parts[1] in FORBIDDEN_SRC_PACKAGES:
                offenders.append(imp)
        self.assertEqual(offenders, [], msg="forbidden imports in __init__: " + str(offenders))
```

Note: matches the shape of `tests/unit/test_repo_layer_rules.py` so the two layer-rule tests read the same way.

- [ ] **Step 2: Run the layer-rule test (expect pass)**

```bash
python3 -m unittest tests.unit.test_layer_rule_config -v
```

Expected: 3 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_layer_rule_config.py
git -c user.email=codex@local -c user.name=codex commit -m "test(config): add AST layer-rule for src/config/"
```

---

## Task 11: Add the end-to-end manual test

**Files:**
- Create: `tests/manual/test_config_end_to_end.py`

- [ ] **Step 1: Implement the manual test**

```python
"""End-to-end smoke test for the config layer (config-001).

This is a runnable sanity check, NOT production code. It proves that:

  1. Default MeetingRecapConfig composes 5 sub-configs with paper defaults.
  2. A custom .env.test file overrides via MEETING_RECAP_<SUB>__<FIELD>.
  3. Process env vars beat .env file values.
  4. _env_file=None skips the file.
  5. Invalid cross-field combos raise ConfigError (which is ValidationError).
  6. The resulting config plugs into model-001 types: chunking.chunk_size
     bounds the number of utterances per Chunk.
  7. extra="forbid" rejects unknown env vars.

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
        assert cfg.text_tiling.window_size == 30
        assert cfg.text_tiling.stride == 10
        assert cfg.chunking.chunk_size == 8
        assert cfg.highlights.extractive_window == 10
        assert cfg.abstractive.context_window == 512
        assert cfg.language.tag == "vi"


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
            assert cfg.chunking.chunk_size == 12
            assert cfg.text_tiling.stride == 20
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
            assert cfg.chunking.chunk_size == 16
        finally:
            os.unlink(env_path)
            _clear_recap_env()

    def test_env_file_none_skips_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env.test", delete=False) as f:
            f.write("MEETING_RECAP_CHUNKING__CHUNK_SIZE=99\n")
            env_path = f.name
        try:
            cfg = MeetingRecapConfig(_env_file=None)
            assert cfg.chunking.chunk_size == 8  # default
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
        from src.types import TranscriptIngestionRequest
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
        assert all(len(c.utterances) <= cfg.chunking.chunk_size for c in chunks)
        # At least one chunk hits the cap (370 utt / 8 = 46 full + 1 partial).
        assert any(len(c.utterances) == cfg.chunking.chunk_size for c in chunks)


class ExtraForbidTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_recap_env()

    def test_unknown_top_level_env_var_rejected(self) -> None:
        os.environ["MEETING_RECAP_BLOOPER"] = "1"
        try:
            with self.assertRaises(ConfigError):
                MeetingRecapConfig(_env_file=None)
        finally:
            _clear_recap_env()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the manual test (expect pass)**

```bash
python3 tests/manual/test_config_end_to_end.py
```

Expected: all 7 tests pass with `OK`.

- [ ] **Step 3: Commit**

```bash
git add tests/manual/test_config_end_to_end.py
git -c user.email=codex@local -c user.name=codex commit -m "test(config): add end-to-end manual smoke for config layer"
```

---

## Task 12: Add `src/config/README.md` quickstart

**Files:**
- Create: `src/config/README.md`

- [ ] **Step 1: Write the README**

```markdown
# Config layer (`src/config/`)

Tunable hyper-parameters for the meeting-recap pipeline. Every paper-
derived magic number lives in exactly one place and is env-overridable.

## Quickstart

```python
from src.config import MeetingRecapConfig

cfg = MeetingRecapConfig()            # reads ./.env (if present)
cfg = MeetingRecapConfig(_env_file=None)  # skip .env entirely
cfg = MeetingRecapConfig(_env_file=".env.test")  # alternate file
```

Override a single field from the shell:

```bash
export MEETING_RECAP_CHUNKING__CHUNK_SIZE=12
export MEETING_RECAP_TEXT_TILING__STRIDE=20
python -m src.something
```

Point the env file at a different path:

```bash
export MEETING_RECAP_ENV_FILE=.env.production
```

## Env-var reference

| Sub-config | Field | Env var | Default |
|---|---|---|---|
| `TextTilingConfig` | `window_size` | `MEETING_RECAP_TEXT_TILING__WINDOW_SIZE` | 30 (paper-1 §3.3) |
| `TextTilingConfig` | `stride` | `MEETING_RECAP_TEXT_TILING__STRIDE` | 10 (paper-1 §3.3) |
| `TextTilingConfig` | `smoothing` | `MEETING_RECAP_TEXT_TILING__SMOOTHING` | "mean" |
| `TextTilingConfig` | `cutoff_policy` | `MEETING_RECAP_TEXT_TILING__CUTOFF_POLICY` | "mean+2std" |
| `ChunkingConfig` | `chunk_size` | `MEETING_RECAP_CHUNKING__CHUNK_SIZE` | 8 (paper-2 §3.3) |
| `ChunkingConfig` | `overlap` | `MEETING_RECAP_CHUNKING__OVERLAP` | 0 |
| `HighlightsConfig` | `extractive_window` | `MEETING_RECAP_HIGHLIGHTS__EXTRACTIVE_WINDOW` | 10 (paper-2 §3.3) |
| `AbstractiveConfig` | `context_window` | `MEETING_RECAP_ABSTRACTIVE__CONTEXT_WINDOW` | 512 (paper-2 §3.3) |
| `LanguageConfig` | `tag` | `MEETING_RECAP_LANGUAGE__TAG` | "vi" |
| `LanguageConfig` | `model_variant` | `MEETING_RECAP_LANGUAGE__MODEL_VARIANT` | "bert-base-multilingual-cased" |
| `MeetingRecapConfig` | `device` | `MEETING_RECAP_DEVICE` | "auto" |
| `MeetingRecapConfig` | `data_dir` | `MEETING_RECAP_DATA_DIR` | "data/eval_vi" |
| `MeetingRecapConfig` | `artifacts_dir` | `MEETING_RECAP_ARTIFACTS_DIR` | "docs/generated" |

## Cross-field rules

* `TextTilingConfig.stride <= window_size`
* `ChunkingConfig.overlap < chunk_size`
* `LanguageConfig.tag="zh"` ⇒ `model_variant="bert-base-chinese"`
* `LanguageConfig.tag in ("en","vi")` ⇒ `model_variant="bert-base-multilingual-cased"`

Violations raise `ConfigError` (a typed alias of `pydantic.ValidationError`)
at construction time.
```

- [ ] **Step 2: Commit**

```bash
git add src/config/README.md
git -c user.email=codex@local -c user.name=codex commit -m "docs(config): add README quickstart + env-var table"
```

---

## Task 13: Run the full regression suite

- [ ] **Step 1: Run the full unit suite**

```bash
python3 -m unittest discover -s tests -v 2>&1 | tail -20
```

Expected: green. Test count must be ≥ 130 (was 92 after model-002 review; config-001 adds 39 unit + 3 layer-rule + 7 manual = +49 → 141).

If the count is lower, count the actual tests with:

```bash
python3 -m unittest discover -s tests -v 2>&1 | grep -E '^test_' | wc -l
```

- [ ] **Step 2: Run the manual end-to-end test**

```bash
python3 tests/manual/test_config_end_to_end.py
```

Expected: 7 tests pass with `OK`.

- [ ] **Step 3: Run the layer-rule test in isolation (sanity)**

```bash
python3 -m unittest tests.unit.test_layer_rule_config -v
```

Expected: 3 tests pass.

- [ ] **Step 4: Verify `.env` integration gap is closed**

The `QUALITY_SCORE.md` Config row says "Skeleton code complete; .env loading not integration-tested". This task closes that gap. If the regression suite above is green, the gap is closed.

---

## Task 14: Update feature_list, QUALITY_SCORE, progress, and move the plan

- [ ] **Step 1: Update `feature_list.json`**

Find the `config-001` block and change `"status": "not_started"` to `"status": "passing"`, and add an `evidence` list (mirror the style of the `model-001` and `model-002` blocks in the same file). The new evidence should mention:

* 6 config modules in `src/config/`
* 39 unit tests + 3 layer-rule tests + 7 manual e2e tests
* Full regression: 141/141 (or actual count) tests pass
* End-to-end manual demo at `tests/manual/test_config_end_to_end.py`

- [ ] **Step 2: Update `docs/QUALITY_SCORE.md`**

* **Architectural Layers > Config row**: change `C` → `B`. Update the `Key Gaps` cell to "None blocking; .env loading integrated via `MeetingRecapConfig(_env_file=...)`; layer rule AST check green".
* **Benchmark Snapshots table**: append a new row dated today with harness variant `config-001-config`, completion rate `100% (XX/XX)`, defects before review `0`, and a one-line note like "Config layer with 5 sub-configs + 1 compose, full env-var override contract, layer-rule AST check green; closes .env integration gap".

- [ ] **Step 3: Update `progress.md`**

Add a new section between the existing `model-002 — Code Review & Fixes` and the end of file, following the style of the previous `model-002` section:

```markdown
## config-001 — Centralized Tunable Hyperparameters (2026-07-05)

**Status:** passing

- Implemented `src/config/{_base,errors,text_tiling,chunking,highlights,abstractive,language,recap,__init__}.py` (9 modules).
- 5 sub-configs (TextTilingConfig / ChunkingConfig / HighlightsConfig / AbstractiveConfig / LanguageConfig) are independently instantiable and frozen.
- MeetingRecapConfig composes all 5 with `env_prefix="MEETING_RECAP_"`, `env_nested_delimiter="__"`, and an overridable `_env_file`. Defaults match paper-1 §3.3 and paper-2 §3.3 exactly.
- ConfigError is a typed alias of pydantic.ValidationError so call sites can `except ConfigError` and still get `.errors()`.
- AST layer-rule test (test_layer_rule_config.py) enforces no imports from `src/repo/`, `src/service/`, `src/runtime/`, `src/ui/`, `src/types/`.
- End-to-end manual test (tests/manual/test_config_end_to_end.py) exercises default flow, custom .env.test, env-beats-file, `_env_file=None`, cross-field rejection, model-001 round-trip, and `extra="forbid"` rejection.
- 39 new unit tests + 3 layer-rule tests + 7 manual tests. Full suite green.

**Verification:** `python3 -m unittest discover -s tests -v` and `python3 tests/manual/test_config_end_to_end.py` both green.
```

- [ ] **Step 4: Create the active plan file**

Create `docs/exec-plans/active/config-001-centralized-config.md`. Copy the structure from `docs/exec-plans/completed/model-002-model-loader.md` (Objective / Scope / Verification path / Risks / Progress log / Open decisions) and fill it for config-001.

- [ ] **Step 5: Move the plan to `completed/`**

After the implementation is fully green and all docs are updated, move the plan to `docs/exec-plans/completed/config-001-centralized-config.md` and append a final `## Verification at archive time` section that records the green-test command and its result.

- [ ] **Step 6: Commit the doc updates**

```bash
git add feature_list.json docs/QUALITY_SCORE.md progress.md docs/exec-plans/
git -c user.email=codex@local -c user.name=codex commit -m "docs(config-001): close out plan, update feature_list + quality + progress"
```

---

## Self-Review (executed by the plan author)

### 1. Spec coverage

| Spec section | Task |
|---|---|
| D1 (pydantic-settings foundation) | Task 1 (add dep) |
| D2 (file-per-config) | Tasks 2-9 (each module + tests) |
| D3 (ConfigError alias) | Task 2 |
| D4 (5 sub-configs, defaults paper-anchored, env-overridable) | Tasks 3-7 |
| D5 (MeetingRecapConfig compose, env_prefix, _env_file) | Task 8 |
| D6 (layer rule) | Task 10 |
| Test plan (~47 tests) | Tasks 3-11 |
| End-to-end manual test | Task 11 |
| Verification commands | Task 13 |
| Risks R1-R5 | Task 1 (R1), Task 8 (R2), Task 10 (R3), Task 11 (R4), Task 8 (R5) |
| Out-of-scope items | Acknowledged in spec, not re-implemented |
| DoD | Task 13 (regression green) + Task 14 (docs) |

No gaps found.

### 2. Placeholder scan

Searched for "TBD", "TODO", "implement later", "fill in details", "similar to Task N", "add appropriate". Result:

- All tests use `unittest.TestCase` and `self.assertRaises(ConfigError)` (project convention; pytest is not in `pyproject.toml`). Env-var cleanup uses `unittest.mock.patch.dict(os.environ, ...)` mirroring the existing `tests/unit/test_model_loader.py` pattern.
- Task 10 layer-rule AST test: matches the shape of the existing `test_repo_layer_rules.py` and explicitly forbids `src/types`, `src/repo`, `src/service`, `src/runtime`, `src/ui` imports. The helper deliberately ignores `if TYPE_CHECKING:` bodies to allow future forward refs.

### 3. Type / name consistency

- `ConfigError` is defined in `src/config/errors.py` and used everywhere: in tests via `from src.config.errors import ConfigError`, and re-exported via `src/config/__init__.py`. ✓
- `TextTilingConfig`, `ChunkingConfig`, `HighlightsConfig`, `AbstractiveConfig`, `LanguageConfig`, `MeetingRecapConfig` are all defined exactly once and imported everywhere by their canonical names. ✓
- Field names match: `window_size`, `stride`, `smoothing`, `cutoff_policy`, `chunk_size`, `overlap`, `extractive_window`, `context_window`, `tag`, `model_variant`, `device`, `data_dir`, `artifacts_dir` — all consistent across tasks. ✓
- `MeetingRecapConfig(_env_file=...)` kwarg name matches the pydantic-settings public API. ✓
- `device` field type is `Literal["auto","cpu","cuda"]`. README + env table use lowercase strings. Consistent. ✓

