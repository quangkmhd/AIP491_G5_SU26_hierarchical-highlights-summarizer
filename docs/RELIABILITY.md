# RELIABILITY.md

This file defines how the system proves it is healthy and restartable.

## Standard Paths

- Bootstrap: `uv sync` (once `pyproject.toml` is filled in; for now the project has no Python deps)
- Unit tests: `python3 -m unittest discover -s tests -v`
- End-to-end smoke test: `python3 tests/manual/test_meeting_committee_sample.py`
- Start app or service: `uv run src/runtime/cli.py` (not yet implemented; depends on `api-001` / `ui-001`)
- Debug or inspect runtime: `uv run python -m pdb src/runtime/cli.py`

## Required Runtime Signals

- Structured logs for startup and critical flows (current: Python `logging` only)
- Health checks for key services (planned in `api-001`)
- Trace or timing data for slow paths (model loading, TextTiling, summarization) when available
- User-visible error states for recoverable failures (the `HierarchicalRecap.status` and `MeetingProcessResponse.error` fields exist for this)

## Golden Journeys

- **Loading a transcript and building a typed `HierarchicalRecap`**
  Path: `python3 tests/manual/test_meeting_committee_sample.py`
  Verifies: Types layer accepts the first Vietnamese committee meeting
  (370 utterances, 8 ground-truth segments), chunks each segment into
  <=8-utterance blocks, and round-trips through JSON without loss.

- **Running the unit suite end-to-end**
  Path: `python3 -m unittest discover -s tests -v`
  Verifies: 39 tests across `Utterance`, `DialogueTranscript`, `Chunk`,
  `SegmentResult`, `Highlight`, `HierarchicalRecap`, API schemas, and the
  Vietnamese committee sample. Currently green.

- **`POST /api/v1/meetings/process` end-to-end** (planned)
  Path: `uv run src/runtime/api.py` + curl
  Verifies: a request with `flat_texts` materializes into a `DialogueTranscript`
  that respects `MAX_UTTERANCES`, and the response carries a populated recap.

- **Generating topic segment bounds matching ground truth** (planned)
  Path: `python3 tests/integration/test_text_tiling.py` (TBD)
  Verifies: TextTiling service places boundaries at +/- 1 utterance of the
  ground-truth splits in `data/eval_vi/meeting_committee.json`.

Each golden journey should have a repeatable verification path and clear failure
signals.

## Reliability Rules

- No feature is complete if the system cannot restart cleanly afterward.
- Runtime failures should be diagnosable from repo-local signals (logs, JSON
  recap files, unit test output).
- If a repeated failure mode appears, add a benchmark or guardrail for it.
- Cleanup is part of reliability, not a separate concern.
- Layer rule is mechanical: an AST scan in
  `tests/manual/test_meeting_committee_sample.py` (or a future import-linter
  job) must show zero cross-layer imports from `src/types/` into
  `config`/`repo`/`service`/`runtime`.
