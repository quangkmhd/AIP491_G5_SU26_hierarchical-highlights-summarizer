# config-001 — Centralize Tunable Hyperparameters (Design Spec)

**Date:** 2026-07-05
**Status:** Approved (pending written review)
**Area:** `config`
**Related plan:** `docs/exec-plans/active/config-001-centralized-config.md` (to be created)
**Layer position:** `Types -> Config -> Repo -> Service -> Runtime -> UI`

## Goal

Expose every paper-derived magic number in the meeting-recap pipeline
as a named, validated, env-overridable configuration object so the
pipeline can be tuned without editing service code.

After this plan:

- Every paper hyper-parameter lives in exactly one place in code
  (the `Field(default=...)` on a Pydantic-Settings sub-config).
- Every default can be overridden via an environment variable of the
  form `MEETING_RECAP_<SUB>__<FIELD>` (or via the constructor kwarg).
- A single `MeetingRecapConfig` composes all sub-configs and is the
  only object the orchestrator needs to consume.
- Invalid combinations (e.g. `stride > window`, `tag="zh"` with
  `model_variant="bert-base-multilingual-cased"`) raise a typed
  `ConfigError` at construction time, not later at inference.
- A `.env` file is supported out of the box and overridable at
  runtime via `MEETING_RECAP_ENV_FILE`.

## Decisions (locked)

### D1. Foundation: Pydantic-Settings

- Use `pydantic-settings` `BaseSettings` (MIT, Apache-2.0 compatible
  with the project's Pydantic v2 stack at `src/types/_base.py`).
- `pydantic-settings` v2.x is the version range; pin to `>=2.0,<3.0`
  in `pyproject.toml` to match the existing Pydantic v2 pin.
- Reason: Pydantic-Settings already implements the env-var,
  `.env`-file, nested-config, and `Field(ge=...)` validation
  contract we need; re-implementing it on top of stdlib would add
  drift and bug surface.

### D2. Module structure: file-per-config

```
src/config/
├── __init__.py            # re-export public surface
├── _base.py               # ConfigBase: frozen BaseSettings
├── errors.py              # ConfigError = pydantic.ValidationError
├── text_tiling.py         # TextTilingConfig
├── chunking.py            # ChunkingConfig
├── highlights.py          # HighlightsConfig
├── abstractive.py         # AbstractiveConfig
├── language.py            # LanguageConfig
├── recap.py               # MeetingRecapConfig
└── README.md              # quickstart + env-var table
```

- One entity per file, matching the style of `src/types/`.
- Each sub-config is **independently instantiable** for isolated unit
  testing; `MeetingRecapConfig` is the only one wired to read
  `.env` and apply `env_prefix`.
- `_base.py` defines `ConfigBase(BaseSettings)` with
  `model_config = SettingsConfigDict(extra="forbid",
  case_sensitive=False, validate_default=True)`. All sub-configs and
  `MeetingRecapConfig` inherit it.

### D3. Error semantics: `ConfigError` is an alias of `ValidationError`

- `src/config/errors.py` defines
  `class ConfigError(pydantic.ValidationError): ...`.
- Sub-config validators raise Pydantic errors as usual; the alias
  exists so call sites can `except ConfigError` and still get the
  full Pydantic `.errors()` structure (used by FastAPI 422 in
  `runtime-001`).
- Rationale: keeps the door open for typed catching without
  breaking Pydantic's well-defined error format.

### D4. Sub-config schema (each field = one paper hyper-parameter)

Every field below has a `default` in code (one place) and an env-var
override of the form `MEETING_RECAP_<SUB>__<FIELD>` (handled by
`env_nested_delimiter="__"`).

| Sub-config | Field | Type | Default (paper) | Validator |
|---|---|---|---|---|
| `TextTilingConfig` | `window_size` | int (ge=1) | 30 (paper-1 §3.3) | `@field_validator` |
| | `stride` | int (ge=1) | 10 (paper-1 §3.3) | |
| | `smoothing` | Literal["mean","median","ema"] | "mean" | |
| | `cutoff_policy` | Literal["mean","mean+2std","depth_knee"] | "mean+2std" | |
| | | | | `@model_validator(mode="after")`: `stride <= window_size` |
| `ChunkingConfig` | `chunk_size` | int (ge=1) | 8 (paper-2 §3.3) | |
| | `overlap` | int (ge=0) | 0 | `@model_validator(mode="after")`: `overlap < chunk_size` |
| `HighlightsConfig` | `extractive_window` | int (ge=1) | 10 (~106 tokens, paper-2 §3.3) | |
| `AbstractiveConfig` | `context_window` | int (ge=1) | 512 (paper-2 §3.3) | |
| `LanguageConfig` | `tag` | Literal["vi","en","zh"] | "vi" (project extends paper-1) | |
| | `model_variant` | Literal["bert-base-multilingual-cased","bert-base-chinese"] | "bert-base-multilingual-cased" | `@model_validator`: `tag=="zh"` requires `model_variant=="bert-base-chinese"`; `tag in ("en","vi")` requires `model_variant=="bert-base-multilingual-cased"` |

- All sub-configs are `frozen=True` (immutable; safe to share across
  threads and across the orchestrator pipeline).
- Defaults are **paper-anchored**: every default cites the section
  that justifies it.

### D5. `MeetingRecapConfig` composes and reads env

```python
class MeetingRecapConfig(ConfigBase):
    model_config = SettingsConfigDict(
        env_prefix="MEETING_RECAP_",
        env_nested_delimiter="__",
        env_file=os.getenv("MEETING_RECAP_ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
        validate_default=True,
    )
    text_tiling: TextTilingConfig = Field(default_factory=TextTilingConfig)
    chunking:    ChunkingConfig    = Field(default_factory=ChunkingConfig)
    highlights:  HighlightsConfig  = Field(default_factory=HighlightsConfig)
    abstractive: AbstractiveConfig = Field(default_factory=AbstractiveConfig)
    language:    LanguageConfig    = Field(default_factory=LanguageConfig)
    device:         Literal["auto","cpu","cuda"] = "auto"
    data_dir:       Path = Path("data/eval_vi")
    artifacts_dir:  Path = Path("docs/generated")
```

- Sub-configs use `default_factory` so each instance gets its own
  validated object (Pydantic v2 supports this for nested models).
- Env var precedence: process env > `.env` file > `default_factory`
  sub-config default. Guaranteed by Pydantic-Settings.
- `_env_file=None` skips the file (kwarg override).
- `extra="forbid"` rejects unknown env vars (e.g.
  `MEETING_RECAP_BLOOPER=1` raises `ConfigError`).

### D6. Layer rule (mechanical, not by convention)

- `src/config/` may import from: stdlib, third-party (`pydantic`,
  `pydantic_settings`, `pathlib`, `os`, `typing`).
- `src/config/` MUST NOT import from: `src/repo/`, `src/service/`,
  `src/runtime/`, `src/ui/`, `src/types/`. (Types are an exception if
  we ever need a type alias, but for `config-001` no types import is
  needed.)
- Enforced by `tests/unit/test_layer_rule_config.py`, an AST scan
  identical in shape to the rule that already exists for `src/repo/`
  in `model-002`.

## Test Plan

| Test file | Coverage | Min tests |
|---|---|---|
| `tests/unit/test_config_text_tiling.py` | defaults = (30,10,"mean","mean+2std"); reject stride>window; env override; `ConfigError` shape | 8 |
| `tests/unit/test_config_chunking.py` | defaults (8,0); reject overlap≥chunk_size; env override | 5 |
| `tests/unit/test_config_highlights.py` | default extractive_window=10; reject ≤0; env override | 4 |
| `tests/unit/test_config_abstractive.py` | default context_window=512; reject ≤0 | 3 |
| `tests/unit/test_config_language.py` | default ("vi", "bert-base-multilingual-cased"); reject tag/variant mismatch; env override | 5 |
| `tests/unit/test_config_recap.py` | compose đúng defaults; env_prefix mapping (`MEETING_RECAP_CHUNKING__CHUNK_SIZE=12` ⇒ `chunking.chunk_size=12`); `_env_file=None` skip; `extra="forbid"` reject unknown env; `ConfigError` is `ValidationError` | 12 |
| `tests/unit/test_layer_rule_config.py` | AST scan: no imports from higher layers | 3 |
| `tests/manual/test_config_end_to_end.py` | (kept out of CI) end-to-end: env-loaded config → `model-001` `DialogueTranscript` round-trip + custom `.env.test` + env-beats-file + `_env_file=None` skip + `extra` rejection | 7 |
| **Total** | | **~47** |

## Verification Commands

```bash
# 1. Static layer rule
python3 -m unittest tests.unit.test_layer_rule_config -v

# 2. Config unit suite
python3 -m unittest discover -s tests/unit -p "test_config_*.py" -v

# 3. Full suite (regression — must keep model-001/model-002 green)
python3 -m unittest discover -s tests -v

# 4. End-to-end manual demo
python3 tests/manual/test_config_end_to_end.py
```

## Risks

- **R1**: `pydantic-settings` is a new runtime dep. Mitigation: pin
  to the same minor family as Pydantic v2; both MIT-licensed.
- **R2**: `env_nested_delimiter="__"` could collide with env vars
  that legitimately contain `__`. Mitigation: no current
  paper-derived var uses `__`; tests cover the happy path.
- **R3**: AST layer-rule might false-positive on
  `if TYPE_CHECKING:` blocks. Mitigation: scan ignores bodies inside
  `if TYPE_CHECKING:` guards.
- **R4**: The empty `.env` at repo root will load 0 keys; this is
  the expected MVP behavior (defaults from code). End-to-end test
  asserts this explicitly.
- **R5**: `MeetingRecapConfig.device="auto"` does not yet drive
  `model_loader`; the orchestrator will resolve it. The device
  semantics are owned by `model-002` for now; this config simply
  records the user preference.

## Out of Scope (deferred)

- `LLMConfig` / `PromptConfig` for Vistral-7B-Chat (own feature once
  `svc-005` / `svc-006` start).
- `ModelCheckpointConfig` env-overridable (the existing `model-002`
  `MockLLMBackbone` / `ModelKind` enum already cover this; can be
  migrated to `ConfigBase` later as a one-file follow-up).
- Hot-reload of config at runtime (Pydantic-Settings has the
  `register_settings` hook, not needed at MVP).
- YAML/TOML config (only `.env` at MVP per project conventions).

## Definition of Done

- All 5 sub-configs + `MeetingRecapConfig` exist with the schema above.
- All ~47 tests listed in the Test Plan pass.
- `python3 -m unittest discover -s tests -v` is green (regression
  intact for `model-001` 38/38 and `model-002` 92/92).
- Layer-rule AST check passes.
- `progress.md` Session 003 entry recorded.
- `docs/QUALITY_SCORE.md` Config layer: C → B.
- `feature_list.json` `config-001` status: `not_started` → `passing`.
- The repository can restart cleanly from the standard startup path.
