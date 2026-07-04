# ARCHITECTURE.md

This file is the top-level map of the system. It should stay concise and point
to deeper documents when needed.

## System Shape

- Product: LLM-Powered Hierarchical Meeting Recap System with Topic Segmentation
- Primary user workflow: Ingest meeting transcripts, segment by topic using CoherenceNet (NSP BERT) TextTiling, and generate hierarchical meeting minutes.
- Runtime surfaces: cli / services
- Source of truth for product behavior: `docs/papers/`

## Domain Map

| Domain | Purpose | Primary Entry Points | Related Spec |
|--------|---------|----------------------|--------------|
| `Topic Segmentation` | `Identifying coherent topics using NSP BERT & TextTiling` | `src/service/text_tiling.py` | `docs/papers/improving-unsupervised-dialogue-topic-segmentation.md` |
| `Hierarchical Recap` | `Meeting summarization, action items, chapters generation` | `src/service/segmenter_service.py` | `docs/papers/llm-powered-meeting-recap-system.md` |

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

| Concern | Approved Boundary | Notes |
|--------|-------------------|-------|
| Logging and tracing | `Standard Python logging` | `[structured only, console allowed for CLI]` |
| Auth | `N/A` | `[token/session rules]` |
| External APIs | `HuggingFace Transformers` | `[local model loading]` |
| Feature flags | `N/A` | `[ownership]` |

## Current Hot Spots

- `CoherenceNet / NSP BERT integration with HuggingFace pipeline`
- `Data loading and boundary scoring logic`

## Change Checklist

When you touch architecture-relevant code:

1. Update this file if the domain map or allowed boundaries changed.
2. Update the related design doc in `docs/design-docs/` if the reasoning changed.
3. Add or update an executable check if the rule should be enforced mechanically.
