# Config layer (`src/config/`)

Tunable hyper-parameters for the meeting-recap pipeline. Every paper-
derived magic number lives in exactly one place and is env-overridable.

## Quickstart

```python
from src.config import MeetingRecapConfig

cfg = MeetingRecapConfig()                # reads ./.env (if present)
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

All env vars are prefixed with `MEETING_RECAP_` and use `__` as a
nested delimiter. Example: `MEETING_RECAP_CHUNKING__CHUNK_SIZE=12`
overrides `cfg.chunking.chunk_size`.

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

## Sub-config direct env override

Each sub-config can also be instantiated directly (e.g. in unit
tests) and env-overridden using the **bare field name** (no prefix,
no nested delimiter). Example: `WINDOW_SIZE=45` overrides
`TextTilingConfig.window_size` if you construct `TextTilingConfig()`
in that process.

```python
import os
os.environ["WINDOW_SIZE"] = "45"
from src.config import TextTilingConfig
TextTilingConfig().window_size  # 45
```

## Cross-field rules

* `TextTilingConfig.stride <= window_size`
* `ChunkingConfig.overlap < chunk_size`
* `LanguageConfig.tag="zh"` ⇒ `model_variant="bert-base-chinese"`
* `LanguageConfig.tag in ("en","vi")` ⇒ `model_variant="bert-base-multilingual-cased"`

Violations raise `ConfigError` (a typed alias of `pydantic.ValidationError`)
at construction time.

## Error semantics

`ConfigError` is a module-level alias of `pydantic.ValidationError`.
`except ConfigError` catches every Pydantic validation failure
(`extra="forbid"`, `ge`/`le`, `@model_validator`, etc.) and exposes
the full `.errors()` payload.

> **Implementation note:** Pydantic v2's `ValidationError` is
> implemented in Rust. Python subclasses of it do **not** match
> `isinstance` against the runtime class, so `ConfigError` is a
> module-level alias rather than a subclass.
