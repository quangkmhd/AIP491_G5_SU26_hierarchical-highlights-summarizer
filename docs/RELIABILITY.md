# RELIABILITY.md

This file defines how the system proves it is healthy and restartable.

## Standard Paths

- Bootstrap: `uv sync`
- Verification: `import-linter`
- Start app or service: `uv run src/runtime/cli.py`
- Debug or inspect runtime: `uv run python -m pdb src/runtime/cli.py`

## Required Runtime Signals

- structured logs for startup and critical flows
- health checks for key services
- trace or timing data for slow paths when available
- user-visible error states for recoverable failures

## Golden Journeys

- `Running CLI end-to-end on a transcript JSON to output hierarchical recap`
- `Validating strictly layered architecture using import-linter`
- `Generating proper Topic Segment bounds matching ground truth`

Each golden journey should have a repeatable verification path and clear failure
signals.

## Reliability Rules

- No feature is complete if the system cannot restart cleanly afterward.
- Runtime failures should be diagnosable from repo-local signals.
- If a repeated failure mode appears, add a benchmark or guardrail for it.
- Cleanup is part of reliability, not a separate concern.
