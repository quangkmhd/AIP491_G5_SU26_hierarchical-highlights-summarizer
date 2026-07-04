# PRODUCT_SENSE.md

This file captures durable product judgment that agents cannot infer reliably
from code alone.

## Product Core

- **Primary user**: Information workers who attend long meetings or catch up
  asynchronously.
- **Job to be done**: Convert unstructured meeting transcripts into a
  structured, readable hierarchy of topics, key points, and action items.
- **Main frustration to remove**: Reading through unstructured transcripts
  or missing context from flat summaries.
- **Quality bar for acceptance**: Accurate topic boundaries mirroring human
  segmentation; high semantic coherence between chunks; summaries written in
  the third person so the recap feels objective.

## Product Rules

- Favor user-visible reliability over feature count.
- Treat ambiguous behavior as a spec gap, not as permission to guess.
- If implementation changes what users see or trust, update the matching spec.
- Use product specs for concrete flows, and use this file for cross-cutting
  product priorities.

## UX Vocabulary vs Model Vocabulary

The recap paper uses two vocabularies for the same domain entities. We keep
them aligned by exposing both:

| Model enum member     | UX label       | Wire JSON value      |
|-----------------------|----------------|----------------------|
| `HighlightType.KEY_POINT`  | "AI note"     | `"key_point"`        |
| `HighlightType.ACTION_ITEM`| "AI task"     | `"action_item"`      |

The canonical wire value is the model vocabulary. UX labels ("note" / "task"
in English, "ghi chú" / "việc cần làm" in Vietnamese) are applied at the
i18n boundary, not in the enum, to avoid coupling the data layer to a single
language.

## No-Go Patterns

- Hidden destructive actions (deleting highlights without confirmation,
  silently dropping over-sized transcripts).
- Silent failure without user feedback (a `HierarchicalRecap.status = FAILED`
  must carry an `error` message; bare `None` is not acceptable).
- Unclear source of truth for visible state (the recap JSON file is the
  source of truth; the UI is a renderer).
- Features that cannot be explained in one sentence (e.g. "highlights
  extraction" -> "extract a list of key-points and action items from each
  segment using a BART pipeline").
- Loading meeting transcripts from the network during local development --
  ingestion must work fully offline so the system is reproducible.
