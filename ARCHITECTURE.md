# ARCHITECTURE.md

This file is the top-level map of the system. It should stay concise and point
to deeper documents when needed.

## System Shape

- Product: Streaming LLM-Powered Hierarchical Meeting Recap System with Topic Segmentation
- Primary user workflow: Ingest a meeting transcript, segment by topic using lexical Sliding TextTiling (BoW + cosine + multi-scale depth), and stream chapter cards (segment + chunk + title) to the user as soon as the pipeline produces them. Highlights pipeline (paper-2 DR1) is out of scope.
- Runtime surfaces: cli (NDJSON) / services (FastAPI SSE)
- Source of truth for product behavior: `docs/papers/` + `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md`

## Domain Map

| Domain               | Purpose                                                                                                   | Primary Entry Points                                                | Related Spec                                                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `Topic Segmentation` | `Identifying coherent topics using lexical Sliding TextTiling (BoW + cosine + multi-scale depth)`  | `src/service/text_tiling.py`, `src/segmenters/sliding_texttiling.py`     | `docs/papers/improving-unsupervised-dialogue-topic-segmentation.md`                                                            |
| `Hierarchical Recap` | `Meeting summarization, chapter titles, rolling summaries (deBERTa, mocked at MVP), streaming end-to-end` | `src/service/meeting_recap_orchestrator.py` (StreamingOrchestrator) | `docs/papers/llm-powered-meeting-recap-system.md` + `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md` |

## Layer Model

Use a fixed directional model so agents do not invent ad hoc architecture:

`Types -> Config -> Repo -> Service -> Runtime -> UI`

Cross-cutting concerns should enter through explicit provider or adapter
boundaries instead of reaching across layers directly.

## Hard Dependency Rules

- Lower layers must not depend on higher layers.
- UI must not bypass runtime or service contracts.
- Data access must enter through repositories or equivalent adapters.
- Shared utilities must remain generic and must not accumulate domain logic.
- New dependencies should be justified in the matching plan or design doc.

## Cross-Cutting Interfaces

| Concern             | Approved Boundary                           | Notes                                                                                                  |
| ------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Logging and tracing | `Standard Python logging`                   | `structured only, console allowed for CLI`                                                             |
| Auth                | `N/A`                                       | `token/session rules`                                                                                  |
| External APIs       | `HuggingFace Transformers`                  | `local model loading; cpt_4000.pth is the user-fine-tuned checkpoint`                                  |
| Feature flags       | `MODEL_LOAD_LLM` env var                    | `0 = MockLLMBackbone (offline CI); 1 = real gemma-4-E2B-it-qat-GGUF`                                   |
| Streaming transport | `sse-starlette` for HTTP / `ndjson` for CLI | `event contract in docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md Section 6` |

## Current Hot Spots

- `Sliding TextTiling multi-scale depth aggregation (radii=[3,5,10,15,20], z-score + mean)`
- `SlidingTextTilingService threshold cutoffs (τ = μ + α·σ)`
- `StreamingOrchestrator: 6-event end-to-end pipeline with deferred title inference`
- `FastAPI SSE route + CLI NDJSON runner (not yet implemented)`

## Service Map

| Service                            | File                                        | Layer   | Depends On                                               | Streaming?                                             |
| ---------------------------------- | ------------------------------------------- | ------- | -------------------------------------------------------- | ------------------------------------------------------ |
| `SlidingTextTilingService`         | `src/service/text_tiling.py`                | Service | `SlidingTextTilingConfig` (Config)                       | yes — sliding depth-score array                        |
| `ChunkingService`                  | `src/service/chunking_service.py`           | Service | (none)                                                   | yes — 8-utt chunk accumulator                          |
| `HierarchicalSummarizationService` | `src/service/hierarchical_summarization.py` | Service | `ModelLoader` (Repo), `MockLLMBackbone` (Repo)           | yes — title deferred, chunk summary synchronous at MVP |
| `StreamingOrchestrator`            | `src/service/meeting_recap_orchestrator.py` | Service | All above + `ModelLoader` (Repo)                         | yes — main entry point (6 event types)                 |

## Change Checklist

When you touch architecture-relevant code:

1. Update this file if the domain map or allowed boundaries changed.
2. Update the related design doc in `docs/design-docs/` if the reasoning changed.
3. Add or update an executable check if the rule should be enforced mechanically.
