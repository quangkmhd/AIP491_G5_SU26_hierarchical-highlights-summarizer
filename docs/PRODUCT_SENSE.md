# PRODUCT_SENSE.md

This file captures durable product judgment that agents cannot infer reliably
from code alone.

## Product Core

- Primary user: Information workers who attend long meetings or catch up asynchronously.
- Job to be done: Convert unstructured meeting transcripts into a structured, readable hierarchy of topics, key points, and action items.
- Main frustration to remove: Reading through unstructured transcripts or missing context from flat summaries.
- Quality bar for acceptance: Accurate topic boundaries mirroring human segmentation; high semantic coherence between chunks.

## Product Rules

- Favor user-visible reliability over feature count.
- Treat ambiguous behavior as a spec gap, not as permission to guess.
- If implementation changes what users see or trust, update the matching spec.
- Use product specs for concrete flows, and use this file for cross-cutting
  product priorities.

## No-Go Patterns

- Hidden destructive actions
- Silent failure without user feedback
- Unclear source of truth for visible state
- Features that cannot be explained in one sentence
