# config-001 — Centralize Tunable Hyperparameters (ACTIVE)

## Objective

Implement the Config layer: a `ConfigBase` shared base class and 5 sub-configs
(`TextTilingConfig`, `ChunkingConfig`, `HighlightsConfig`, `AbstractiveConfig`,
`LanguageConfig`) plus a composing `MeetingRecapConfig` that is the single
entry point for the orchestrator. All defaults paper-anchored; all
overridable via env vars.

## Scope

- `src/config/_base.py`: `ConfigBase` (frozen `BaseSettings` with `extra=forbid`, `validate_default=True`).
- `src/config/errors.py`: `ConfigError` as module-level alias of `pydantic.ValidationError`.
- `src/config/text_tiling.py`: `TextTilingConfig` (window=30, stride=10, smoothing, cutoff_policy; paper-1 §3.3).
- `src/config/chunking.py`: `ChunkingConfig` (chunk_size=8, overlap=0; paper-2 §3.3).
- `src/config/highlights.py`: `HighlightsConfig` (extractive_window=10; paper-2 §3.3).
- `src/config/abstractive.py`: `AbstractiveConfig` (context_window=512; paper-2 §3.3).
- `src/config/language.py`: `LanguageConfig` (tag="vi", model_variant; paper-1 §3 + vi extension).
- `src/config/recap.py`: `MeetingRecapConfig` (composes all 5; `env_prefix=MEETING_RECAP_`, `env_nested_delimiter=__`, `env_file=os.getenv("MEETING_RECAP_ENV_FILE", ".env")`).
- `src/config/__init__.py`: re-exports the public API with `__all__`.
- `tests/unit/test_config_*.py`: 6 unit test files (40+ tests).
- `tests/unit/test_layer_rule_config.py`: AST scan enforcing no imports from higher layers.
- `tests/manual/test_config_end_to_end.py`: end-to-end smoke test (7 tests) including model-001 round-trip on the Vietnamese committee meeting.
- `src/config/README.md`: quickstart + env-var table.

## Out of Scope

- `LLMConfig` / `PromptConfig` for Vistral-7B-Chat (own feature once `svc-005` / `svc-006` start).
- `ModelCheckpointConfig` env-overridable (the existing `model-002` `MockLLMBackbone` / `ModelKind` enum already cover this; can be migrated to `ConfigBase` later).
- Hot-reload of config at runtime (Pydantic-Settings has the `register_settings` hook, not needed at MVP).
- YAML/TOML config (only `.env` at MVP per project conventions).

## Verification path

```bash
# Unit suite
python3 -m unittest discover -s tests -v

# Manual end-to-end demo
python3 tests/manual/test_config_end_to_end.py

# Layer-rule test
python3 -m unittest tests.unit.test_layer_rule_config -v
```

## Risks and blockers

- **R1**: `pydantic-settings` is a new runtime dep. Mitigation: pin to the same minor family as Pydantic v2; both MIT-licensed. (Status: pinned in pyproject.toml as `pydantic-settings>=2.0,<3.0`.)
- **R2**: `env_nested_delimiter="__"` could collide with env vars that legitimately contain `__`. Mitigation: no current paper-derived var uses `__`; tests cover the happy path.
- **R3**: AST layer-rule might false-positive on `if TYPE_CHECKING:` blocks. Mitigation: MVP has none; helper can be extended later.
- **R4**: The empty `.env` at repo root will load 0 keys; this is the expected MVP behavior (defaults from code). End-to-end test asserts this explicitly.
- **R5**: `MeetingRecapConfig.device="auto"` does not yet drive `model_loader`; the orchestrator will resolve it. The device semantics are owned by `model-002` for now; this config simply records the user preference.

## Open decisions

None at this time. All 6 decisions (D1-D6) from the spec are locked.

## Progress log

- 2026-07-05: Started (branch `feat/config-001-centralized-config`).
- 2026-07-05: All 14 plan tasks executed. 47 new tests; full suite 144/144.
- 2026-07-05: 3 plan corrections applied (see plan doc "Implementation findings"):
  1. `ConfigError` = module-level alias (not subclass)
  2. Sub-configs use bare field names for env override
  3. `extra="forbid"` applies to kwargs only, not to env vars
- 2026-07-05: All docs updated (feature_list.json, QUALITY_SCORE.md, progress.md, spec, plan).

## Verification at archive time

- Date: 2026-07-05
- Green command: `python3 -m unittest discover -s tests -v`
- Result: **144/144 OK** in ~27s
- Green command: `python3 tests/manual/test_config_end_to_end.py`
- Result: **7/7 OK** in ~0.05s
- Green command: `python3 -m unittest tests.unit.test_layer_rule_config -v`
- Result: **3/3 OK**
- Branch: `feat/config-001-centralized-config`
- Commits: 11 commits (337af7c .. 65eebce)
- Files: 9 src + 7 test + 3 docs (spec amendment, plan note, this archive move) = 19 files.
- Plan corrections applied during execution: 3 (documented in plan's "Implementation findings" section + spec D3/D5).


## Code review

- 2026-07-05: inline code review (`docs/generated/review-2026-07-05-config-001.md`).
  Verdict: ready to merge with 1 Minor fix applied (unused imports in test_config_recap.py) and 1 Minor filed as tech debt (`_default_env_file()` class-body resolution).
  No critical or important issues.
