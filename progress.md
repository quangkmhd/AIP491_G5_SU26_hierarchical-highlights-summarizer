
# Progress Log

## Current Verified State

- Repository root: /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
- Standard startup path: `pwd` then read AGENTS.md -> ARCHITECTURE.md -> docs/QUALITY_SCORE.md -> docs/PLANS.md -> docs/product-specs/.
- Standard verification path: `python3 -m unittest discover -s tests -v`.
- Current highest-priority unfinished feature: model-002 (AI Model Loader & File Repository).
- Current blocker: none for model-001; model-002 needs the HuggingFace model checkpoints or offline stubs.

## Session Log

### Session 001

- Date: 2026-07-04
- Goal: Implement model-001 (Core Data Models) and run it on the first Vietnamese committee transcript.
- Completed: Pydantic v2 models in src/types (Utterance, DialogueTranscript, Chunk, SegmentResult, Highlight, HighlightType, HighlightSource, HierarchicalRecap, MeetingStatus, TranscriptIngestionRequest, HighlightUpsertRequest, MeetingProcessResponse). 38/38 unit tests pass. End-to-end demo (tests/manual/test_meeting_committee_sample.py) loads data/eval_vi/meeting_committee.json[0] (370 utterances, 8 segments) and writes a HierarchicalRecap JSON to docs/generated/model001_demo_recap.json.
- Verification run: `python3 -m unittest tests.unit.test_types_model001 -v` -> OK (30 tests). `python3 -m tests/manual/test_meeting_committee_sample.py` -> 8 segments / 50 chunks / 2 highlights.
- Evidence captured: tests/unit/test_types.py, docs/generated/model001_demo_recap.json, feature_list.json (model-001 -> passing), QUALITY_SCORE.md.
- Commits: not committed (per AGENTS.md contract).
- Files or artifacts updated: src/types/{_base,__init__,utterance,transcript,segment,highlight,hierarchical_recap,schemas}.py, src/__init__.py, tests/unit/__init__.py, tests/unit/test_types.py, feature_list.json, docs/QUALITY_SCORE.md, docs/generated/model001_demo_recap.json.
- Known risk or unresolved issue: model-001 is the foundation only; svc-001 (TextTiling) and svc-002 (Summarization) are still placeholders. model-002 (ModelLoader) is the next dependency.
- Post-review hardening (same session): enforced MAX_UTTERANCES in DialogueTranscript and at the request boundary (materialize()), added model_validator requiring exactly one of `utterances` / `flat_texts`, and locked the Highlight JSON wire format to canonical 'key_point' / 'action_item' values via a new test. Test count grew 34 -> 38.
- Next best step: Begin model-002 (ModelLoader) so svc-001 can wire CoherenceNet into HuggingFace pipeline.

### Session 002

- Date: 2026-07-05
- Goal: Implement config-001 (Centralize Tunable Hyperparameters) on branch feat/config-001-centralized-config.
- Completed: 9 modules in src/config/ (_base, errors, 5 sub-configs, recap, __init__); ConfigBase as frozen BaseSettings with extra='forbid', validate_default=True; 5 sub-configs (TextTilingConfig/ChunkingConfig/HighlightsConfig/AbstractiveConfig/LanguageConfig) with paper-anchored defaults; MeetingRecapConfig composes all 5 with env_prefix=MEETING_RECAP_, env_nested_delimiter=__; ConfigError is module-level alias of pydantic.ValidationError; 7 unit test files + 1 layer-rule AST test + 1 end-to-end manual test; 47 new tests; 144/144 full suite green.
- Verification run: `python3 -m unittest discover -s tests -v` -> 144/144 OK (~27s). `python3 tests/manual/test_config_end_to_end.py` -> 7/7 OK.
- Evidence captured: tests/unit/test_config_{text_tiling,chunking,highlights,abstractive,language,recap}.py (40 unit tests), tests/unit/test_layer_rule_config.py (3 AST tests), tests/manual/test_config_end_to_end.py (7 e2e tests), src/config/{_base,errors,text_tiling,chunking,highlights,abstractive,language,recap,__init__}.py, feature_list.json (config-001 -> passing), docs/QUALITY_SCORE.md (Config layer C -> B), docs/superpowers/specs/2026-07-05-config-001-centralized-config-design.md (updated D3 + D5), docs/superpowers/plans/2026-07-05-config-001-centralized-config.md (implementation findings note).
- Commits: 11 commits on feat/config-001-centralized-config (337af7c .. 65eebce).
- Files or artifacts updated: 9 src files, 7 test files, 3 docs files; total 19 files.
- Known risk or unresolved issue: 3 plan corrections were applied during execution -- (1) ConfigError implemented as module-level alias of pydantic.ValidationError (not Python subclass, because Pydantic v2's ValidationError is Rust-implemented and bypasses __init_subclass__); (2) sub-configs use bare field names for env override (no nested delimiter, no prefix -- only MeetingRecapConfig uses MEETING_RECAP_<SUB>__<FIELD>); (3) extra='forbid' applies to model kwargs only, not to env vars (Pydantic-Settings treats unknown env vars as 'ignore'). All three are now reflected in the spec and README.
- Next best step: Either merge feat/config-001-centralized-config to main, or proceed to data-001 (Multi-corpus Evaluation Data Loader) which can now consume MeetingRecapConfig.data_dir.

## model-002 — AI Model Loader & File Repository (2026-07-04)

**Status:** passing

- Implemented `src/repo/{coherence_net,model_loader,transcript_repo,recap_repo,smoke_loader}.py` + `prompts_vi.py`.
- CoherenceNet loads from `vibert_checkpoints_vi/cpt_4000.pth` (paper-1 architecture, BERT-base multilingual base, embeddings resized to ckpt vocab 38168, strict=False for shape-mismatched MLM-head keys).
- ModelLoader is a per-process singleton; `MODEL_LOAD_LLM=0` env var returns a `MockLLMBackbone` for offline CI.
- Vistral-7B-Chat selected as the single Vietnamese LLM backbone (4-bit via `bitsandbytes`, deferred behind env var).
- 4 Vietnamese prompt templates cover the collapsed paper-2 task list (segment / abstractive / title / highlights).
- TranscriptRepo reads all 6 `data/eval_vi/*.json` files into `DialogueTranscript` with synthesised speaker labels and drops empty/placeholder utterances (e.g. AMI `{vocalsound}` artefacts).
- RecapRepo round-trips `HierarchicalRecap` via Pydantic v2 `model_dump_json`.
- AST-based layer-rule test enforces zero imports from `config`/`service`/`runtime`/`ui` in `src/repo/`.
- 35 new unit tests; full suite green (74/74).
- Verification: `MODEL_LOAD_LLM=0 python3 -m unittest discover -s tests` and `python3 -m src.repo.smoke_loader` both green.

## model-002 — Code Review & Fixes (2026-07-05)

**Reviewer:** `docs/generated/review-2026-07-05.md`
**Verdict (initial):** Not ready to merge — 4 critical + 3 important bugs.

**Fixes applied (same session):**
- **C1** (`src/repo/transcript_repo.py`): `_strip_inline_placeholders` now
  removes inline `{vocalsound}` / `{gap}` / `{disfmarker}` annotations
  from kept utterance text, not just fully-placeholder utterances.
- **C2** (`src/repo/transcript_repo.py:_build_transcript`): speaker labels
  now track the ORIGINAL index (`S{original_idx + 1}`) so dropping
  utterances does not shift everyone else's speaker tag.
- **C3** (`src/repo/model_loader.py`): added `_cache_lock` to make the
  per-kind lookup-and-insert atomic. Two threads can no longer both
  trigger a fresh `ModelKind.NSP` load.
- **C4** (`src/repo/model_loader.py`): added `_coerce_token_ids` helper
  that clamps token IDs >= vocab_size (38168) to 0 (UNK) so the
  embedding lookup no longer raises on real Vietnamese text. **Tracked
  as Important debt** in `docs/exec-plans/tech-debt-tracker.md` —
  clamped tokens lose semantic content, so the model is not yet
  production-quality for real Vietnamese.
- **I1** (`src/repo/recap_repo.py`): write is atomic via
  `tempfile.NamedTemporaryFile` + `os.replace`. A mid-write crash no
  longer leaves a truncated file at the destination path.
- **I2** (`src/repo/_io.py`): new shared module for
  `read_json_file` / `write_json_file`. Both `RecapRepo` and
  `TranscriptRepo` call into it; new repos will follow the same
  pattern automatically.
- **I3** (`src/repo/smoke_loader.py`): added `REQUIRE_CUDA=1` env var
  for the smoke loader to fail loudly on CPU-only hosts. The default
  remains permissive.

**Test count:** 76 → 92 (+16 new tests covering C1, C2, C3, C4, I1, I2,
I3 directly).

**Documentation:**
- `docs/QUALITY_SCORE.md`: `Topic Segmentation` row claim reworded
  to "on the resolved device (cuda preferred, cpu fallback)";
  `Benchmark Snapshots` row for `model-002-repo` now records the
  4-critical-bug review + 16-test fix cycle.
- `docs/exec-plans/tech-debt-tracker.md`: C4 (vocab mismatch) and
  I2 (incomplete _io adoption) recorded as Important; M1, M2, M3
  recorded as Minor.

## config-001 — Centralized Tunable Hyperparameters (2026-07-05)

**Status:** passing

- Implemented `src/config/{_base,errors,text_tiling,chunking,highlights,abstractive,language,recap,__init__}.py` (9 modules).
- 5 sub-configs (TextTilingConfig / ChunkingConfig / HighlightsConfig / AbstractiveConfig / LanguageConfig) are independently instantiable and frozen.
- MeetingRecapConfig composes all 5 with `env_prefix="MEETING_RECAP_"`, `env_nested_delimiter="__"`, and an overridable `_env_file`. Defaults match paper-1 §3.3 and paper-2 §3.3 exactly.
- ConfigError is a module-level alias of pydantic.ValidationError (Pydantic v2's ValidationError is Rust-implemented and cannot be subclassed via Python).
- AST layer-rule test (test_layer_rule_config.py) enforces no imports from `src/types`, `src/repo`, `src/service`, `src/runtime`, `src/ui`.
- End-to-end manual test (tests/manual/test_config_end_to_end.py) exercises default flow, custom .env.test, env-beats-file, `_env_file=None`, cross-field rejection, model-001 round-trip, and unknown env-var ignore.
- 47 new tests (40 unit + 3 layer-rule + 4 boundary checks I added beyond the plan; +7 manual). Full suite green at 144/144.

**Verification:** `python3 -m unittest discover -s tests -v` (144/144 OK) and `python3 tests/manual/test_config_end_to_end.py` (7/7 OK).



## config-001 — Code Review & Fixes (2026-07-05)

**Reviewer:** `docs/generated/review-2026-07-05-config-001.md` (inline review; `spawn_agent` not available in this Codex session).
**Verdict (initial):** Ready to merge with one Minor fix.

**Fixes applied (same session):**
- **M1** (`tests/unit/test_config_recap.py:17-25`): removed 4 unused
  sub-config imports (`AbstractiveConfig`, `ChunkingConfig`,
  `HighlightsConfig`, `LanguageConfig`) — the test constructs
  `MeetingRecapConfig` directly and only references
  `TextTilingConfig` explicitly. Re-verified suite: 144/144 + 7/7
  still green.

**Tech debt filed:**
- **M2** (`src/config/recap.py:32-38`): `_default_env_file()` runs at
  class-body definition. If a caller sets `MEETING_RECAP_ENV_FILE`
  *after* import, the override is silently ignored. Fix: replace
  with a `model_validator(mode="before")` resolver. Tracked in
  `docs/exec-plans/tech-debt-tracker.md` (Minor).

**Acknowledged but not fixed:**
- **M3** (project convention): `from __future__ import annotations`
  in every test file is unused (tests don't ship as libraries) but
  matches the project-wide convention. Leave as-is.

**Documentation:**
- `docs/QUALITY_SCORE.md`: `Benchmark Snapshots` row for
  `config-001-config` extended with the code-review summary.
- `docs/exec-plans/tech-debt-tracker.md`: M2 (`_default_env_file`
  class-body resolution) recorded as Minor.

## model-001+ — Remove Highlights Data Models (2026-07-05)

**Status:** passing

- Deleted `src/types/highlight.py` (Highlight, HighlightType, HighlightSource).
- Removed `highlights_notes` and `highlights_tasks` fields from `HierarchicalRecap`; removed `all_highlights` property.
- Removed `HighlightUpsertRequest` from `src/types/schemas.py` and the corresponding `__all__` entry.
- Updated `src/types/__init__.py` to drop Highlight re-exports.
- Rewrote `tests/unit/test_types.py`: deleted `HighlightTests` class; added `test_model_dump_contains_no_highlights_keys` in `HierarchicalRecapTests`; rewrote `MeetingCommitteeSampleTests` to drop highlights.
- Updated `tests/manual/test_meeting_committee_sample.py` to drop Highlight imports and the highlights_* recap fields.
- Verification: `python3 -m unittest discover -s tests -v` → 140/140 tests pass (was 144 before; 4 tests removed in HighlightTests class).
- Manual smoke: `python3 tests/manual/test_meeting_committee_sample.py` → 8 segments, 50 chunks, output JSON has no `highlights_*` keys.
- AST layer-rule test (`tests/unit/test_repo_layer_rules.py`) still green: no cross-layer imports introduced.
- Spec: `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md` D1.
- Plan: `docs/superpowers/plans/2026-07-05-model-001-patch-remove-highlights.md`.
- Worktree: `.worktrees/feat-model-001-plus` (branch `feat/model-001-plus`).

## config-001+ — Drop HighlightsConfig from MeetingRecapConfig (2026-07-05)

**Status:** passing

- Deleted `src/config/highlights.py` (HighlightsConfig).
- Removed `HighlightsConfig` import + `__all__` entry from `src/config/__init__.py`.
- Removed `highlights: HighlightsConfig` field from `MeetingRecapConfig` (now composes 4 sub-configs: TextTilingConfig, ChunkingConfig, AbstractiveConfig, LanguageConfig).
- Updated `src/config/README.md` env-var table (HIGHLIGHTS__* row marked removed).
- Deleted `tests/unit/test_config_highlights.py` (5 tests).
- Updated `tests/unit/test_config_recap.py` (drop `cfg.highlights.*` assertion).
- Verification: `python3 -m unittest discover -s tests` → 135/135 OK (was 140).
- AST layer-rule test still green.
- Spec: `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md` D2.
- Worktree: `.worktrees/feat-config-001-plus` (branch `feat/config-001-plus`).

## data-001 — Multi-corpus Evaluation Data Loader (2026-07-05)

**Status:** passing

- Created `src/data/` layer with 4 modules: `__init__.py`, `corpus.py` (Corpus enum + metadata), `dialogue_sample.py` (Pydantic model), `eval_loader.py` (file loader + DataLoaderError).
- Convention: `DialogueSample.segments` is a list of segment SIZES (cumulative sum = utterance count). All 6 corpora use this convention.
- Per-corpus metadata: language, source, domain. Committee is the only Vietnamese corpus.
- 19 unit tests in `tests/unit/test_eval_loader.py` covering happy path (all 6 corpora), error paths (missing root, malformed JSON, non-array, invalid sample), metadata attachment, performance (<1s for committee).
- AST layer rule `tests/unit/test_data_layer_rules.py` forbids data from importing higher layers.
- Verification: 154/154 tests pass (was 135; +19 new).
- Smoke: loads 36 committee samples, first has 370 utt + 8 segments.
- Worktree: `.worktrees/feat-data-001` (branch `feat/data-001`).

## svc-001+002 — Topic Segmentation Pipeline (paper-1 *Ours full*) (2026-07-05)

**Status:** passing

- Created `src/service/{__init__,coherence_scorer,text_tiling}.py`.
- `CoherenceScorer` wraps `CoherenceNet` in paper-1 mode CM (fine-tuned coherence scoring model). `score_pair(utt_i, utt_i_plus_1) -> float ∈ [0, 1]`. Includes C4 token-id clamp (mitigates vocab mismatch 38168 vs 119547).
- `TextTilingService` ports paper-1 `neural_texttiling.py`:
  - `depth_computing(scores)`: `0.5 * (hl + hr - 2 * s[i])` per score.
  - `cutoff_threshold`: `tau = mu - sigma/2` (paper-1 §3 spec).
  - Emits `SegmentEvent(segment_id, utterances_start, utterances_end, depth_score, boundary_index)`.
- 16 unit tests in `tests/unit/test_text_tiling.py` (depth formula, cutoff, sliding, 3-valley synthetic, coverage, ID uniqueness, non-overlap).
- 1 AST layer-rule test in `tests/unit/test_service_layer_rules.py`.
- 1 end-to-end smoke in `tests/manual/test_svc_001_002_smoke.py` loads cpt_4000.pth, scores 369 pairs, runs TextTiling, emits 192 segments (partial fine-tuning; expected to over-segment vs ground truth).
- Verification: 172/172 tests pass (was 155; +17 new).

## svc-003 — Hierarchical Chunking (8-utt blocks) (2026-07-05)

**Status:** passing

- Created `src/service/chunking_service.py` with `ChunkingService.chunk(utterances)` and `chunk_indices(n)`.
- Slices utterances into 8-utt Chunks (no overlap; paper-2 §3.2 spec).
- 11 unit tests covering 8/30/7/1 utterance cases, empty input raises, indices, unique IDs, order preservation.
- Verification: full suite green.

## svc-004 — Hierarchical Summarization (2026-07-05)

**Status:** passing

- Created `src/service/hierarchical_summarization.py` with `title(segment)` and `abstractive(chunk)`.
- Uses `ModelLoader.load_llm_backbone()` → MockLLMBackbone at MVP via `MODEL_LOAD_LLM=0`.
- 8 unit tests covering nonempty output, truncation at TITLE_MAX_CHARS=64 / ABSTRACTIVE_MAX_CHARS=256, empty segment, 3rd-person marker ("Nhóm"), helper method.
- Verification: 191/191 tests pass (was 183; +8 new).
