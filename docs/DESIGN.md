# DESIGN.md

This file is the design entrypoint. Keep it brief and use it to route into the
more detailed files under `docs/design-docs/`.

## Purpose

Record durable product and system design decisions that should survive beyond a
single chat, sprint, or reviewer memory.

## Read This When

- you need the current design philosophy
- you are about to introduce a new pattern
- you need to know which design decisions are settled versus still open

## Canonical Design Docs

- `docs/design-docs/index.md`: index of accepted, proposed, and deprecated docs
- `docs/design-docs/core-beliefs.md`: project-wide agent-first beliefs
- `docs/design-docs/system-architecture.md`: definitive architecture for the
  Hierarchical Meeting Recap system (data flow, API contracts, NFRs)
- `docs/design-docs/models-and-roadmap.md`: data models (Types layer) and the
  layered implementation roadmap
- `docs/design-docs/paper-integration.md`: how the two source papers combine

## Design Rules

- Keep design docs small and current.
- Prefer one doc per decision area.
- Link design docs from plans and specs when a change depends on them.
- If a design rule becomes operationally critical, promote it into an automated
  check or update `ARCHITECTURE.md`.

## Recently Settled Decisions (2026-07-04)

- **Types layer uses Pydantic v2** (`BaseSchema` in `src/types/_base.py`) with
  `extra="forbid"`, `populate_by_name`, `str_strip_whitespace`. See
  `docs/design-docs/models-and-roadmap.md` for the model inventory.
- **Utterance is frozen** (raw input data); `Highlight` is mutable through
  `toggle_star` / `toggle_check` (interactive UI affordance).
- **Constants are `ClassVar`** (e.g. `Chunk.MAX_CHUNK_SIZE = 8`,
  `DialogueTranscript.MAX_UTTERANCES = 5000`), not per-instance fields.
- **HighlightType canonical values** are `"key_point"` / `"action_item"` on the
  wire. UX labels ("note" / "task") are applied at the i18n boundary, not in the enum
  (Vietnamese UI uses "ghi chú" / "việc cần làm", so a hard-coded English alias
  would be wrong anyway).
- **Layer rule** is mechanically enforced: an AST scan in
  `tests/manual/test_meeting_committee_sample.py` confirms `src/types/` has
  zero imports from `config`/`repo`/`service`/`runtime`.
