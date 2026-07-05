# Tech Debt Tracker

This file tracks deferred work and follow-ups that are out of scope for
the current active plan. Items here are non-blocking for shipping the
current milestone but should be addressed before the next major one.

## Severity Legend

- **Important** -- affects correctness, performance, or UX in a way users
  can notice.
- **Minor** -- cleanup, polish, or documentation that improves legibility
  but does not change observable behavior.

## Open Items

### Minor (from model-001 self-review, 2026-07-04)

- **No `__all__` in `src/types/schemas.py`**
  - File: `src/types/schemas.py`
  - Issue: `__init__.py` already names the three classes explicitly, so
    this is fine, but a local `__all__` would tighten the module's
    public surface.
  - Fix: add `__all__ = ["TranscriptIngestionRequest", "HighlightUpsertRequest", "MeetingProcessResponse"]`.
  - Owner: next agent touching `schemas.py`.

- **No `repr` customization for large models**
  - File: `src/types/transcript.py`, `src/types/hierarchical_recap.py`
  - Issue: Pydantic's default repr prints every utterance, which is
    noisy for a 370-utterance transcript.
  - Fix: add `__repr_args__` that limits nested repr depth, or set
    `model_config = ConfigDict(repr=False)` for these two models.
  - Owner: next agent touching debugging UX.

- **Deterministic UUID in demo is undocumented**
  - File: `tests/manual/test_meeting_committee_sample.py`
  - Issue: the demo uses `UUID(int=(dial_id + 1) * 10**12)` so the
    output JSON is reproducible. Production code uses `uuid4()`.
  - Fix: a one-line comment explaining "deterministic for diffable demo
    output" so the next reader doesn't think the production code is
    supposed to be deterministic.
  - Owner: next agent touching the smoke test.

- **No `to_compact_dict()` helper on `HierarchicalRecap`**
  - File: `src/types/hierarchical_recap.py`
  - Issue: `model_dump_json()` includes the full `Chunk.utterances` text,
    which is 243 KB for the Vietnamese committee meeting. The recap
    payload the UI needs is just metadata (segment ranges, titles, rolling
    summaries, highlights) -- the raw utterances already live in the
    source transcript.
  - Fix: add a `to_compact_dict()` method that drops `chunks[].utterances`
    and includes only `chunks[].chunk_id` + `chunks[].rolling_summary`.
  - Owner: next agent implementing `api-001`.

## Resolved Items

(none yet)

### Important (from model-002 code review, 2026-07-05)

- **C4: Tokenizer vocab mismatch (38168 ckpt vs 119547 multilingual base)**
  - File: `src/repo/model_loader.py:113-129` (mitigation); root cause is
    missing 38168-vocab Vietnamese-subset tokenizer.
  - Issue: The pre-trained `cpt_4000.pth` was trained with a Vietnamese-
    subset tokenizer (vocab 38168) that is NOT shipped with the project.
    The repo currently loads `bert-base-multilingual-cased` (vocab
    119547) and mitigates the OOV problem with `_coerce_token_ids` that
    clamps IDs >= 38168 to 0 (UNK). This means the model cannot reliably
    score real Vietnamese text -- clamped tokens lose all semantic
    content and degrade coherence scoring accuracy.
  - Mitigations: (1) obtain the 38168-vocab tokenizer from the model
    author, (2) train a frequency-truncated tokenizer from the
    multilingual vocab that matches the checkpoint, or (3) rebuild the
    CoherenceNet architecture to use a 119547-vocab checkpoint
    (re-train or fine-tune from scratch).
  - Required before: `svc-001` (real Vietnamese inference).
  - Workaround today: `_coerce_token_ids` keeps the embedding lookup
    from raising; tests pass with synthetic IDs in [0, 38167].

- **I2: `src/repo/_io.py` is not yet used by every new repo**
  - File: `src/repo/recap_repo.py:50-72` and `src/repo/transcript_repo.py:69-79`
  - Issue: Both repos now call into `_io.read_json_file`, but
    `RecapRepo.write` re-implements the temp-file + `os.replace` flow
    inline rather than going through a shared `write_json_file` helper.
    The next repo added will copy one of these two patterns.
  - Required before: adding a third repo (e.g. `HighlightsRepo`).

### Important (from config-001 code review, 2026-07-05)

- **I2: Sub-configs inherit bare (unprefixed) env var reads when composed inside `MeetingRecapConfig`**
  - File: `src/config/recap.py:54-58` (the `default_factory=TextTilingConfig` and similar), all sub-config files
  - Issue: When `MeetingRecapConfig()` constructs nested sub-configs via `default_factory`, the sub-config's own `BaseSettings` applies bare, unprefixed env var matching. `WINDOW_SIZE=999` in the process env overrides `cfg.text_tiling.window_size`, bypassing the `MEETING_RECAP_` prefix contract.
  - Impact: High for production — variables set by parent shells, CI systems, or container orchestration that coincidentally match field names silently override configuration.
  - Fix options: (A) Give sub-configs their own `env_prefix` matching nested-delimiter convention; (B) Construct sub-configs in a `model_validator(mode="before")` that temporarily clears bare env vars; (C) Accept and document prominently.
  - Owner: next agent touching config layer or first agent deploying to production.

- **I3: No upper bounds on integer fields — unbounded values can cause memory exhaustion**
  - File: `src/config/text_tiling.py:29-30` (window_size, stride), `src/config/chunking.py:18-19` (chunk_size, overlap), `src/config/abstractive.py:17` (context_window), `src/config/highlights.py:20` (extractive_window)
  - Issue: All integer fields bounded only by `ge=1` (or `ge=0`). A value like `WINDOW_SIZE=2147483647` passes validation and would cause enormous array allocations.
  - Fix: Add `le=` bounds aligned with pipeline limits: window_size/stride ≤500, chunk_size ≤100, context_window ≤32768, extractive_window ≤100.
  - Owner: first agent wiring these fields into orchestrator array allocations.

- **I5: Unvalidated `env_file` path — directory traversal risk**
  - File: `src/config/recap.py:38` (os.getenv + Path resolution), `src/config/recap.py` (_env_file kwarg)
  - Issue: Arbitrary relative or absolute paths accepted via `MEETING_RECAP_ENV_FILE` or `_env_file` kwarg with no traversal validation. Path resolved relative to project root (fix for M5 applied 2026-07-05) but still allows `../../secrets.env`.
  - Fix: Add `@field_validator` rejecting paths with `..` traversal or that resolve outside project root.
  - Owner: next agent touching `recap.py`.

### Minor (from config-001 code review, 2026-07-05)

- **`_default_env_file()` runs at class-body definition**
  - File: `src/config/recap.py:32-38` (function) and `src/config/recap.py:50` (use)
  - Issue: `env_file=_default_env_file()` is evaluated once when `MeetingRecapConfig` is first imported. If a caller sets `MEETING_RECAP_ENV_FILE` *after* import (e.g. in a test setUp), the override is silently ignored and the class falls back to the env-var-or-default value captured at import time.
  - Impact: Low for the current `.env` workflow (file is set once at process start), but a test using the env var directly would surprise.
  - Fix: replace the class-body `env_file=...` with a `model_validator(mode="before")` that reads `os.getenv("MEETING_RECAP_ENV_FILE", ".env")` at construction time.
  - Owner: next agent touching `recap.py` (or first agent that needs the env-var override path).

- **M1: `AbstractiveConfig` unit test missing `EnvOverrideTests` class**
  - File: `tests/unit/test_config_abstractive.py`
  - Issue: Every other sub-config test file has `EnvOverrideTests`; AbstractiveConfig is the only one without.
  - Fix: Add `EnvOverrideTests` with `CONTEXT_WINDOW=1024` env override test.
  - Owner: next agent touching config tests.

- **M2: Partial env-override test coverage for string/optional fields**
  - File: `tests/unit/test_config_chunking.py` (missing `OVERLAP`), `tests/unit/test_config_text_tiling.py` (missing `SMOOTHING`, `CUTOFF_POLICY`), `tests/unit/test_config_language.py` (missing `MODEL_VARIANT`)
  - Issue: Env-override tests exist for some fields but not all; the README documents these env vars but not all are exercise-tested.
  - Fix: Add env-override tests for remaining fields in each `EnvOverrideTests` class.
  - Owner: next agent touching config tests.

- **M3: Boundary `stride == window_size` not explicitly tested**
  - File: `tests/unit/test_config_text_tiling.py`
  - Issue: The cross-field validator allows `stride <= window_size`. The tightest valid config (`stride=10, window=10`) has no explicit success test.
  - Fix: Add `test_stride_equals_window_allowed` constructing `TextTilingConfig(window_size=10, stride=10)` and asserting success.
  - Owner: next agent touching config tests.

- **M4: `data_dir` and `artifacts_dir` accept arbitrary paths with no traversal validation**
  - File: `src/config/recap.py:62-70`
  - Issue: When wired into service/runtime layer, attacker-controlled paths could redirect output to sensitive locations.
  - Fix: Add `@field_validator` ensuring resolved paths stay within project root.
  - Owner: next agent wiring data_dir/artifacts_dir into runtime code.

- **M5: `extra="forbid"` silently ignores unknown `MEETING_RECAP_*` env vars**
  - File: `src/config/_base.py:28`, tested as accepted contract in `tests/unit/test_config_recap.py:107-119`
  - Issue: Typos like `MEETING_RECAP_CHUNKING_CHUNK_SIZE=12` (single underscore) silently fall back to default.
  - Fix: Consider `warnings.warn` for env vars matching `MEETING_RECAP_` prefix but not mapping to any known field.
  - Owner: DX polish pass before production deployment.

### Minor (from model-002 code review, 2026-07-05)

- **M1: `ModelLoader.reset_instance()` does not evict model weights**
  - File: `src/repo/model_loader.py:185-189`
  - Issue: `reset_instance` only nulls the class-level `_instance`. If
    a caller already holds a reference to the old loader, the model
    weights stay loaded in VRAM.
  - Note: Documented as test-only; production code should never call
    `reset_instance`.

- **M2: `coerce_checkpoint_path` is dead code on `CoherenceNet`**
  - File: `src/repo/coherence_net.py:80-88`
  - Issue: A static method on the class that duplicates the check in
    `_load_nsp_weights`. Future maintainers may call it from a new
    service and end up with two divergent implementations.
  - Fix: Delete; if a public validator is needed, move to a module-
    level function in `model_loader.py` and call it from both sites.

- **M3: `CoherenceNet.forward` runs BERT one pair at a time**
  - File: `src/repo/coherence_net.py:62-78`
  - Issue: For a 100-sample batch, this issues 300 separate BERT
    forward passes instead of one batched `[300, L]` forward.
  - Performance impact: ~3-10x slower than the batched version
    (depends on device). The Service layer in `svc-001` will score
    many utterance pairs in tight loops, so this matters at scale.
  - Fix: Stack input dicts across the batch, run BERT once per
    pair-type, then reshape back into `[B, 3, 768]`.
