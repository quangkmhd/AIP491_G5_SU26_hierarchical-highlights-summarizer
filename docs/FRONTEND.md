# FRONTEND.md

This file defines stable frontend expectations so agents do not invent UI
patterns unpredictably. The UI layer (`ui-001`) is not implemented yet; this
file captures the constraints the upcoming Web App must respect.

## UI Principles

- Optimize for clarity before novelty.
- Keep interaction flows discoverable and restartable.
- Prefer a small number of reusable components over one-off variants.
- Accessibility checks are part of normal verification, not polish work.

## User-Facing Surfaces (planned)

The recap paper's UX is the source of truth. From `docs/papers/llm-powered-meeting-recap-system.md` section 3.4:

- **Highlights view**: a list of "key-points" (UI: "AI notes") and
  "action-items" (UI: "AI tasks"). Each action item has editable
  `assigned to` and `date` fields. Each item has a "show context" affordance
  that reveals up to three transcript utterances before and after the
  detection.
- **Hierarchical view**: chapters in chronological order, each with a
  heading, a one-line summary, and a timespan. Clicking the timespan
  reveals a rolling summary with timestamps linked to transcript utterances.
  Key points and action items appear as stars and checkboxes next to
  summaries and chapter titles.

## Guardrails

- Document the design system or component library in `docs/references/`
  when chosen.
- Record key user-facing states: empty, loading, success, error, retry.
- Keep copy, keyboard behavior, and visual hierarchy consistent across flows.
- When a UI bug is fixed, add or update the matching validation step.
- The recap payload the UI receives is the `HierarchicalRecap` JSON dumped
  via `model_dump(mode="json")` (UUIDs as strings, datetimes as ISO-8601).
  The UI must round-trip user edits (chapter title overrides, star/checked
  toggles) via the `PATCH /api/v1/meetings/{id}/segments/{id}` and
  `POST /api/v1/meetings/{id}/highlights` endpoints.

## Verification Expectations

- Capture evidence for critical user journeys (e.g. paste a transcript ->
  receive a hierarchical recap within the 3-minute sync budget).
- Record browser or runtime validation steps in the relevant plan
  (`docs/exec-plans/active/`).
- If visual regressions are common, standardize screenshot or DOM checks
  via `docs/sops/chrome-devtools-validation-loop.md`.
