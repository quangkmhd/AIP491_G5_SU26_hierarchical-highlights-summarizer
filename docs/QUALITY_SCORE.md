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
| `Topic Segmentation` | C | - | Medium | - | Skeleton code exists; coherence scoring + TextTiling not yet wired to HuggingFace models | 2026-07-04 |
| `Hierarchical Recap` | C | - | Medium | - | Skeleton code exists; deBERTa summarization stages are placeholders | 2026-07-04 |
| `Highlights & Action Items` | C | - | Medium | - | Skeleton code exists; BART highlights extraction is placeholder | 2026-07-04 |
| `CLI App` | D | - | Low | - | No runtime layer implemented yet | 2026-07-04 |

## Architectural Layers

| Layer | Grade | Boundary Enforcement | Agent Legibility | Key Gaps | Last Updated |
|-------|-------|---------------------|-----------------|----------|-------------|
| Types | C | - | Medium | Skeleton code complete (5 dataclasses); no validation tests yet | 2026-07-04 |
| Config | C | - | Medium | Skeleton code complete; .env loading not integration-tested | 2026-07-04 |
| Repo | C | - | Medium | Skeleton code complete; HuggingFace model loading is NotImplementedError placeholder | 2026-07-04 |
| Services | C | - | Medium | Four service modules with algorithm skeletons; all ML inference paths are placeholders | 2026-07-04 |
| Runtime | D | - | Low | No runtime layer implemented yet | 2026-07-04 |
| UI | D | - | Low | No UI layer implemented yet | 2026-07-04 |

## Benchmark Snapshots

| Date | Harness Variant | Completion Rate | Retries | Defects Before Review | Notes |
|------|-----------------|----------------|--------|-----------------------|------|
| YYYY-MM-DD | `[baseline / improved / simplified]` | - | - | - | - |

## Simplification Log

| Date | Component Removed | Outcome | Decision |
|------|-------------------|---------|----------|
| YYYY-MM-DD | `N/A` | `N/A` | `N/A` |
