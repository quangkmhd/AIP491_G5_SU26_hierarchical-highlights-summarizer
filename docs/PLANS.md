# PLANS.md

This file defines how execution plans are created, updated, completed, and
archived.

## When A Plan Required

Create an execution plan when work:

- spans more than one session
- changes more than one subsystem
- has non-trivial verification or rollout risk
- depends on open decisions that should be logged

`model-001` did not need a full plan (single session, single layer), but the
plan is now archived at `docs/exec-plans/completed/model-001-types-layer.md`
so the next agent has a baseline.

## Plan Locations

- `docs/exec-plans/active/`: plans currently driving work
- `docs/exec-plans/completed/`: finished plans kept for future agent context
- `docs/exec-plans/tech-debt-tracker.md`: deferred work and follow-ups

## Minimum Plan Sections

- objective
- scope and out-of-scope
- verification path (concrete commands the next agent can copy-paste)
- risks and blockers
- progress log (chronological, with dates and verification runs)
- open decisions

## Operating Rules

- One active plan should have one clearly owned current step.
- Update the plan as work progresses; do not treat it as static prose.
- If a decision changes implementation direction, record it in the plan.
- Move finished plans to `completed/` so agents can still discover prior
  context. The completed plan must end with a "Verification at archive time"
  section that captures the green-test command and its result.
- When an issue is found during a code review but is not in scope of the
  current plan, record it in `tech-debt-tracker.md` (Minor severity) or open
  a follow-up plan (Important or Critical).
