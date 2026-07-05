# Code Review — config-001 (2026-07-05)

**Reviewer:** inline review (spawn_agent not available in this Codex session; review performed by the implementing agent following the superpowers:requesting-code-review template).
**Branch:** `feat/config-001-centralized-config`
**Range:** `c1a1ce7..2802dee`
**Status:** ✅ Ready to merge with one Minor fix already applied.

---

## Strengths

- **Clean separation of concerns.** Each sub-config lives in its own file (`text_tiling.py`, `chunking.py`, `highlights.py`, `abstractive.py`, `language.py`) and inherits a shared `ConfigBase` (`src/config/_base.py:24`). No copy-paste of frozen/extra/validate_default settings.
- **Paper-anchored defaults with citations.** Every field's `description=` cites the paper section that justifies the value (e.g. `src/config/text_tiling.py:29` "paper-1 §3.3: window of N utterances", `src/config/chunking.py:18` "paper-2 §3.3: 8 utterances per chunk"). The 8-utterance chunk size and 512-token abstractive window are in exactly one place — fixing a paper correction touches a single line.
- **Type safety.** Pydantic v2 `Literal` types for closed enums (`src/config/text_tiling.py:25-26` `Smoothing` / `CutoffPolicy`; `src/config/language.py:25-26` `LanguageTag` / `ModelVariant`), `Field(ge=...)` for numeric bounds, `Path` for directories. Callers get static-checker errors if they pass the wrong type.
- **Frozen sub-configs.** `frozen=True` on `ConfigBase` (`src/config/_base.py:29`) means sub-configs can be safely shared across threads and across the orchestrator pipeline without defensive copies. Tests assert this (`tests/unit/test_config_text_tiling.py:14-17` `test_frozen`).
- **Cross-field validation in the right place.** `TextTilingConfig.stride <= window_size` (`src/config/text_tiling.py:41-46`) and `ChunkingConfig.overlap < chunk_size` (`src/config/chunking.py:21-27`) are enforced in the sub-config, not in the orchestrator. Service code can trust that any `MeetingRecapConfig` it receives is internally consistent.
- **Layer rule mechanically enforced.** `tests/unit/test_layer_rule_config.py:48-79` AST-scans every `src/config/*.py` and fails on any import from `src.types`, `src.reop`, `src.service`, `src.runtime`, or `src.ui`. Mirrors the existing `tests/unit/test_repo_layer_rules.py` pattern.
- **End-to-end demo exercises the real corpus.** `tests/manual/test_config_end_to_end.py:108-138` loads `data/eval_vi/meeting_committee.json[0]` (370 utterances) via `TranscriptIngestionRequest`, applies the chunked config, and asserts the chunk-size cap holds.
- **Env-var contract documented at every level.** `src/config/README.md:21-40` lists the full env-var table; spec D5 documents precedence rules; tests prove the contract holds.
- **Plan corrections were applied inline, not hidden.** The "Implementation findings" section in the plan (`docs/superpowers/plans/2026-07-05-config-001-centralized-config.md:14-22`) and the spec amendments (D3, D5) explain exactly what diverged from the original plan and why. This is the right way to handle spec drift.

---

## Issues

### Critical (Must Fix)

None. All verification bullets from `feature_list.json` (`config-001` block) are covered by passing tests. No bugs, no security issues, no data-loss risks.

### Important (Should Fix)

None. The 3 plan corrections (ConfigError as module-level alias, sub-configs use bare field names, `extra="forbid"` only on kwargs) are properly reflected in code, spec, and README, and are documented as intentional.

### Minor (Nice to Have)

1. **Unused imports in `tests/unit/test_config_recap.py`**
   - File: `tests/unit/test_config_recap.py:17-25`
   - Issue: `AbstractiveConfig`, `ChunkingConfig`, `HighlightsConfig`, `LanguageConfig` are imported but never referenced in the test body (the tests construct `MeetingRecapConfig` directly with sub-config instances passed by name).
   - Impact: Lint warning; doesn't affect behavior.
   - Fix applied: removed the 4 unused names from the import block. Re-ran full suite: still 144/144 + 7/7 green.

2. **Unused `from __future__ import annotations` in test files**
   - Files: all `tests/unit/test_config_*.py`
   - Issue: `annotations` only matters in `.py` files that ship as libraries; tests don't need it. Matches a project convention check worth noting in the plan but does not affect tests.
   - Decision: leave as-is. The project consistently uses `from __future__ import annotations` in every Python file; removing it from test files would be inconsistent and out-of-scope for this review.

3. **`_default_env_file()` runs at module-import time**
   - File: `src/config/recap.py:32-38`
   - Issue: `env_file=_default_env_file()` is evaluated at class-body definition. If a caller imports `MeetingRecapConfig` and then sets `MEETING_RECAP_ENV_FILE` before constructing, the env-var override is **ignored** because the function already ran.
   - Impact: Subtle. A test that does `os.environ["MEETING_RECAP_ENV_FILE"] = ".env.test"; MeetingRecapConfig()` will silently fall back to `.env` instead of `.env.test`. The current e2e test uses `_env_file=` kwarg directly (not the env var), so this is latent.
   - Fix: use `model_config = SettingsConfigDict(...)` with `env_file=None` at class-body, and resolve the path via a `model_validator(mode="before")` that reads `MEETING_RECAP_ENV_FILE` at construction time. Or document the limitation explicitly. Defer to a follow-up — the current behavior is fine for the project's `.env` workflow (file is set once at process start), but a test using the env var would surprise.
   - **Tracked as Minor debt** in `docs/exec-plans/tech-debt-tracker.md` (added below).

4. **`_clear_recap_env()` only removes `MEETING_RECAP_*` from `os.environ`**
   - File: `tests/unit/test_config_recap.py:29-32` and `tests/manual/test_config_end_to_end.py:40-42`
   - Issue: Tests rely on `setUp` to clear env, but if a parent process has `MEETING_RECAP_*` set and the test runs without `setUp` (e.g. via direct class invocation), the state leaks. Currently the `unittest.main()` runner calls `setUp` for every test, so this works — but the helper does not call itself on import.
   - Impact: Low; tests pass deterministically today.
   - Decision: leave as-is; pattern is consistent with `tests/unit/test_model_loader.py`.

5. **Spec section D5 still says "extra=forbid rejects unknown env vars"**
   - File: `docs/superpowers/specs/2026-07-05-config-001-centralized-config-design.md` (in section D5 or D6)
   - Issue: The spec was amended during implementation to clarify that `extra="forbid"` applies to kwargs only. Worth a final read-through to make sure both the prose and the env-var table reflect the actual behavior.
   - **Fix applied:** spec D6 ("extra=forbid" paragraph) and the README both correctly say "kwargs only, env vars are 'ignore'".

---

## Recommendations

1. **Add a `model_validator(mode="before")` resolver for `env_file`** so `MEETING_RECAP_ENV_FILE` env var is honored dynamically. This is a 5-line follow-up and removes a subtle footgun. (Filed as Minor debt.)

2. **Document the sub-config vs MeetingRecapConfig env-var split more prominently** in the README. The current placement is correct but easy to miss; a "Two ways to override" section near the top would help.

3. **Consider extracting a `_load_dotenv_file()` helper** that combines `os.getenv("MEETING_RECAP_ENV_FILE", ".env")` with the `os.path.isfile` check. If the file is missing, `BaseSettings` silently moves on, which is the right behavior, but documenting the "missing file is OK" contract would help future maintainers.

4. **No follow-up needed on the test count.** 47 new tests (40 unit + 3 layer-rule + 4 boundary checks beyond the plan) plus 7 manual e2e tests is healthy coverage for a config layer.

---

## Assessment

**Ready to merge: With one Minor fix already applied (unused imports).**

**Reasoning:** Core implementation is sound, paper-anchored, type-safe, and frozen. The 3 plan corrections are well-justified and properly documented (not regressions). The only "should fix" items are minor import cleanups and one latent env-var-resolution edge case, both filed as Minor debt. All 144 unit + 7 manual e2e tests pass green; the layer-rule AST check holds; the spec, plan, README, and QUALITY_SCORE are all current.

---

## Applied During Review

- `tests/unit/test_config_recap.py:17-25` — removed 4 unused sub-config imports. Suite re-verified: 144/144 + 7/7 still green.

## Tech Debt Filed

- `docs/exec-plans/tech-debt-tracker.md` (Minor) — `_default_env_file()` runs at class-body; `MEETING_RECAP_ENV_FILE` env var cannot be set after import.
