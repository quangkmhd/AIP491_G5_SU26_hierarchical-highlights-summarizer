# ARCHITECTURE.md

This file is the top-level map of the system. It should stay concise and point
to deeper documents when needed.

## System Shape

- Product: Streaming LLM-Powered Hierarchical Meeting Recap System with Topic Segmentation
- Primary user workflow: Stream audio from microphone via WebSocket, run VAD + ASR + Speaker Identification in realtime, segment by topic using lexical Streaming Sliding TextTiling (overlapping windows, BoW + cosine + multi-scale depth), and stream chapter cards (segment + chunk + title) to the user as soon as the pipeline produces them. Highlights pipeline (paper-2 DR1) is out of scope.
- Runtime surfaces: cli (NDJSON) / services (FastAPI SSE + WebSocket `/ws`)
- Source of truth for product behavior: `docs/papers/` + `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md`

## Domain Map

| Domain               | Purpose                                                                                                   | Primary Entry Points                                                | Related Spec                                                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `ASR + Speaker`      | `Realtime VAD + ASR (sherpa-onnx Zipformer2) + Speaker ID (wespeaker cosine embedding)` | `src/service/asr_engine.py`, `src/runtime/api.py:/ws`                    | viet_iter3_inference reference                                                                                                 |
| `Topic Segmentation` | `Identifying coherent topics using lexical Streaming Sliding TextTiling (overlapping windows, BoW + cosine + multi-scale depth)`  | `src/service/text_tiling.py`, `src/segmenters/sliding_texttiling.py`     | `docs/papers/improving-unsupervised-dialogue-topic-segmentation.md`                                                            |
| `Hierarchical Recap` | `ViT5 chunk summaries, BARTpho titles from completed topic summaries, streaming end-to-end` | `src/service/meeting_recap_orchestrator.py` (StreamingOrchestrator) | `docs/superpowers/specs/2026-07-11-local-finetuned-recap-models-design.md` |

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
| Model runtime       | `HuggingFace Transformers` + `sherpa-onnx`  | CUDA-only local ViT5 + BARTpho for recap; sherpa-onnx for ASR + VAD + Speaker Embedding                |
| Streaming transport | `sse-starlette` for HTTP / `ndjson` for CLI / WebSocket for realtime audio | `event contract in docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md Section 6` |

## Current Hot Spots

- `Streaming Sliding TextTiling multi-scale depth aggregation in overlapping local windows (window_size=40, stride=5, alpha=1.0)`
- `Streaming Sliding TextTiling local threshold cutoffs (τ = μ_local + α·σ_local)`
- `StreamingOrchestrator: 6-event end-to-end pipeline with deferred title inference`
- `FastAPI SSE route + CLI NDJSON runner (not yet implemented)`

## Service Map

| Service                            | File                                        | Layer   | Depends On                                               | Streaming?                                             |
| ---------------------------------- | ------------------------------------------- | ------- | -------------------------------------------------------- | ------------------------------------------------------ |
| `SlidingTextTilingService`       | `src/service/text_tiling.py`                | Service | `SlidingTextTilingConfig` (Config)                       | yes — local window sliding depth-score array           |
| `ChunkingService`                  | `src/service/chunking_service.py`           | Service | (none)                                                   | yes — 8-utt chunk accumulator                          |
| `HierarchicalSummarizationService` | `src/service/hierarchical_summarization.py` | Service | task-specific ViT5/BARTpho adapters (Repo)               | yes — summaries complete before summary-only title inference |
| `StreamingOrchestrator`            | `src/service/meeting_recap_orchestrator.py` | Service | All above + `ModelLoader` (Repo)                         | yes — main entry point (6 event types)                 |
| `AsrEngine`                        | `src/service/asr_engine.py`                 | Service | `AsrConfig` (Config) + sherpa-onnx models (local files)  | yes — realtime WebSocket mic → VAD → ASR → Speaker ID  |

## Change Checklist

When you touch architecture-relevant code:

1. Update this file if the domain map or allowed boundaries changed.
2. Update the related design doc in `docs/design-docs/` if the reasoning changed.
3. Add or update an executable check if the rule should be enforced mechanically.
