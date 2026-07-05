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
| `Hierarchical Recap` | C | Types layer solid; orchestrator still pending | Medium | - | `HierarchicalRecap` data shape is final; `svc-002` (deBERTa/BART) still placeholder | 2026-07-04 |
| `Highlights & Action Items` | C | Types layer solid; extractor still pending | Medium | - | `Highlight` model + UX alias methods final; `svc-002` (BART) still placeholder | 2026-07-04 |
| `CLI App` | D | - | Low | - | No runtime layer implemented yet (depends on `api-001` / `ui-001`) | 2026-07-04 |

## Architectural Layers

| Layer | Grade | Boundary Enforcement | Agent Legibility | Key Gaps | Last Updated |
|-------|-------|---------------------|-----------------|----------|-------------|
| Types | B | 38/38 unit tests pass; AST scan confirms zero imports from `config`/`repo`/`service`/`runtime` | High | None blocking; canonical-value enum wire format + ClassVar limits enforced; see Minor items in `docs/exec-plans/tech-debt-tracker.md` | 2026-07-04 |
| Config | C | - | Medium | Skeleton code complete; .env loading not integration-tested | 2026-07-04 |
| Repo | B | 5 modules implemented (CoherenceNet, ModelLoader, TranscriptRepo, RecapRepo, smoke_loader); layer-rule AST check green; full unit suite + smoke loader pass; offline mock LLM allows CI without network | High | - | None blocking; real 4-bit Vistral load deferred behind MODEL_LOAD_LLM=1 to keep CI deterministic | 2026-07-04 |
| Services | C | - | Medium | Four service modules with algorithm skeletons; all ML inference paths are placeholders | 2026-07-04 |
| Runtime | D | - | Low | No runtime layer implemented yet | 2026-07-04 |
| UI | D | - | Low | No UI layer implemented yet | 2026-07-04 |

## Benchmark Snapshots

| Date | Harness Variant | Completion Rate | Retries | Defects Before Review | Notes |
|------|-----------------|----------------|--------|-----------------------|------|
| 2026-07-04 | `model-001-types` | 100% (38/38 unit) | 0 | 0 | First Vietnamese committee meeting (dial_id=0) end-to-end round-trip into `HierarchicalRecap` JSON; includes post-review hardening (MAX_UTTERANCES, payload validators, JSON wire-format lock) | 2026-07-04 |
| 2026-07-05 | `model-002-repo` | 100% (92/92 unit, +16 from code review) | 0 | 4 | Repo layer passed 4-critical-bug code review on 2026-07-05; fixes for C1 (inline placeholder strip), C2 (original-index speaker labels), C3 (per-loader cache lock), C4 (token-ID clamp for real Vietnamese text); I1 (atomic RecapRepo.write) + I2 (shared _io.py) + I3 (REQUIRE_CUDA flag) also applied | 2026-07-05 |

## Simplification Log

| Date | Component Removed | Outcome | Decision |
|------|-------------------|---------|----------|
| 2026-07-04 | `SegmentResult.segment_uuid` (duplicate of `segment_id`) | Field removed; one canonical UUID per segment | Kept cleaner; only the unique key was retained |
| 2026-07-04 | `src/types/recap.py` and `src/types/api_schemas.py` | Replaced with `hierarchical_recap.py` and `schemas.py` | Files renamed to match the conceptual entities they contain; no behavior change |
| 2026-07-04 | `tests/unit/test_types_model001.py` and `tests/manual/test_demo_model001.py` | Replaced with `test_types.py` and `test_meeting_committee_sample.py` | Decoupled test names from `feature_list.json` IDs; next agent can find tests by layer / input, not by feature id |
| 2026-07-04 | `HighlightType.note()` / `task()` classmethods | Removed | 0 callers, 0 tests using them; UX labels are applied at the i18n boundary (Vietnamese uses different words than English) so a hard-coded alias would have been wrong anyway |
| 2026-07-04 | 4 paper-2 fine-tuned models (BART/deBERTa) collapsed into 1 Vistral-7B-Chat + 4 prompt templates | Replaced 4 model identifiers with one Vietnamese LLM backbone + 4 prompt templates in `src/repo/prompts_vi.py` | Fine-tuning 4 models impractical; 4-bit Vistral fits RTX 4060 8GB; prompt engineering covers the same 4 task shapes |
