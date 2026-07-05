# QUALITY_SCORE.md

This document tracks whether the repository is getting stronger or weaker over
time.

## Grading Scale

- `A`: verified, legible, stable, boundaries enforced
- `B`: working with minor gaps
- `C`: partially working, notable confusion or instability
- `D`: broken, unsafe, or structurally unclear

## Product Domains

| Domain | Grade | Verification | Agent Legibility | Test Stability | Key Gaps | Last Updated |
|--------|-------|-------------|-----------------|---------------|----------|-------------|
| `Topic Segmentation` | B | Smoke loader loads CoherenceNet from cpt_4000.pth on the resolved device (cuda preferred, cpu fallback); layer rule green | Medium | - | Real inference in svc-001/svc-002 still pending; C4 token-ID clamp mitigates the vocab mismatch | 2026-07-04 |
| `Hierarchical Recap` | B | Streaming orchestrator, API SSE, CLI NDJSON, UI prototype, and eval harness covered by 250/250 tests | High | - | Real Vistral generation remains behind `MODEL_LOAD_LLM=1`; mock backbone is used for deterministic verification | 2026-07-05 |
| `Highlights & Action Items` | N/A | Highlights pipeline intentionally dropped by DR1; no runtime/UI/eval surface exposes it | High | - | None; do not reintroduce highlights_extractive unless a new design decision reverses DR1 | 2026-07-05 |
| `CLI App` | B | CLI process/stream tests include NDJSON output, recap write, nonexistent file, and actionable Fix message for empty JSON arrays | High | - | argparse file-open errors still use argparse's stock message before command context exists | 2026-07-05 |

## Architectural Layers

| Layer | Grade | Boundary Enforcement | Agent Legibility | Key Gaps | Last Updated |
|-------|-------|---------------------|-----------------|----------|-------------|
| Types | B | 38/38 unit tests pass; AST scan confirms zero imports from `config`/`repo`/`service`/`runtime` | High | None blocking; canonical-value enum wire format + ClassVar limits enforced; see Minor items in `docs/exec-plans/tech-debt-tracker.md` | 2026-07-04 |
| `Config` | B | 47/47 unit tests pass; AST scan confirms zero imports from `types`/`repo`/`service`/`runtime`/`ui`; .env loading integrated via `MeetingRecapConfig(_env_file=...)`; env_prefix + env_nested_delimiter mapping covered; `ConfigError` is module-level alias of `pydantic.ValidationError` | High | None blocking | 2026-07-05 |
| Repo | B | 5 modules implemented; layer-rule AST check green; read/write/model load tracing added with stdlib logging to preserve layer rules; full suite green | High | None blocking; real 4-bit Vistral load deferred behind MODEL_LOAD_LLM=1 to keep CI deterministic | 2026-07-05 |
| Services | B | CoherenceScorer, TextTilingService, ChunkingService, HierarchicalSummarizationService, and StreamingOrchestrator covered by focused unit/integration tests | High | Mock LLM backbone remains the default CI path; real quality evaluation depends on future model runs | 2026-07-05 |
| Runtime | B | FastAPI process/SSE + CLI process/stream implemented; request-id middleware, timing logs, validation fix fields, and CLI fix messages covered by tests | High | No auth or production health endpoint yet | 2026-07-05 |
| UI | B | Playwright UI structure tests verify same-origin static serving, required input elements, and no highlights tab | High | Prototype only; no production build pipeline | 2026-07-05 |

## Benchmark Snapshots

| Date | Harness Variant | Completion Rate | Retries | Defects Before Review | Notes |
|------|-----------------|----------------|--------|-----------------------|------|
| 2026-07-04 | `model-001-types` | 100% (38/38 unit) | 0 | 0 | First Vietnamese committee meeting (dial_id=0) end-to-end round-trip into `HierarchicalRecap` JSON; includes post-review hardening (MAX_UTTERANCES, payload validators, JSON wire-format lock) | 2026-07-04 |
| 2026-07-05 | `model-002-repo` | 100% (92/92 unit, +16 from code review) | 0 | 4 | Repo layer passed 4-critical-bug code review on 2026-07-05; fixes for C1 (inline placeholder strip), C2 (original-index speaker labels), C3 (per-loader cache lock), C4 (token-ID clamp for real Vietnamese text); I1 (atomic RecapRepo.write) + I2 (shared _io.py) + I3 (REQUIRE_CUDA flag) also applied | 2026-07-05 |
| 2026-07-05 | `config-001-config` | 100% (144/144 unit, +47 from config-001) | 0 | 0 | Config layer with 5 sub-configs + 1 compose (MeetingRecapConfig), env_prefix=MEETING_RECAP_ + env_nested_delimiter=__ contract, layer-rule AST check green, end-to-end manual demo closes .env integration gap; 3 plan corrections applied during execution (ConfigError as module-level alias, sub-config bare-field env vars, extra='forbid' only on kwargs not env); code review on 2026-07-05 returned 0 critical / 0 important / 3 minor; 1 minor fixed inline (unused imports in test_config_recap.py), 1 minor filed as tech debt (`_default_env_file()` class-body resolution), 1 noted as project convention | 2026-07-05 |
| 2026-07-05 | `runtime-observability` | 100% (250/250 discover) | 1 | 1 | Added centralized logging/tracing, request-id propagation, API/CLI actionable fix suggestions, repo/service telemetry, and regression tests. One layer-rule retry required changing repo modules from `src.logging` imports to stdlib `logging.getLogger`. | 2026-07-05 |

## Simplification Log

| Date | Component Removed | Outcome | Decision |
|------|-------------------|---------|----------|
| 2026-07-04 | `SegmentResult.segment_uuid` (duplicate of `segment_id`) | Field removed; one canonical UUID per segment | Kept cleaner; only the unique key was retained |
| 2026-07-04 | `src/types/recap.py` and `src/types/api_schemas.py` | Replaced with `hierarchical_recap.py` and `schemas.py` | Files renamed to match the conceptual entities they contain; no behavior change |
| 2026-07-04 | `tests/unit/test_types_model001.py` and `tests/manual/test_demo_model001.py` | Replaced with `test_types.py` and `test_meeting_committee_sample.py` | Decoupled test names from `feature_list.json` IDs; next agent can find tests by layer / input, not by feature id |
| 2026-07-04 | `HighlightType.note()` / `task()` classmethods | Removed | 0 callers, 0 tests using them; UX labels are applied at the i18n boundary (Vietnamese uses different words than English) so a hard-coded alias would have been wrong anyway |
| 2026-07-04 | 4 paper-2 fine-tuned models (BART/deBERTa) collapsed into 1 Vistral-7B-Chat + 4 prompt templates | Replaced 4 model identifiers with one Vietnamese LLM backbone + 4 prompt templates in `src/repo/prompts_vi.py` | Fine-tuning 4 models impractical; 4-bit Vistral fits RTX 4060 8GB; prompt engineering covers the same 4 task shapes |
