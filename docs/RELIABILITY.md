# RELIABILITY.md

This file defines how the system proves it is healthy and restartable.

## Standard Paths

- Bootstrap: use the existing Python environment for now; keep `MODEL_LOAD_LLM=0` for deterministic offline verification.
- Unit tests: `MODEL_LOAD_LLM=0 python3 -m unittest discover -v`
- End-to-end smoke test: `python3 tests/manual/test_meeting_committee_sample.py`
- Start API: `MODEL_LOAD_LLM=0 uvicorn src.runtime.api:app --reload`
- Run CLI: `MODEL_LOAD_LLM=0 python3 -m src.runtime.cli stream <transcript.json>`
- Debug or inspect runtime: `MODEL_LOAD_LLM=0 python3 -m pdb -m src.runtime.cli`

## Required Runtime Signals

- Structured logs for startup and critical flows through `src.logging`; default human format, `MEETING_RECAP_LOG_FORMAT=json` for machine parsing.
- Request/CLI tracing with `request_id` and `event` context; FastAPI echoes `X-Request-Id`.
- Trace or timing data for slow paths: request elapsed time, model loading, TextTiling boundary counts, orchestrator totals, repo read/write summaries.
- User-visible error states for recoverable failures: API/CLI errors include actionable `fix` suggestions instead of bare status codes or tracebacks.

## Golden Journeys

- **Loading a transcript and building a typed `HierarchicalRecap`**
  Path: `python3 tests/manual/test_meeting_committee_sample.py`
  Verifies: Types layer accepts the first Vietnamese committee meeting
  (370 utterances, 8 ground-truth segments), chunks each segment into
  <=8-utterance blocks, and round-trips through JSON without loss.

- **Running the unit suite end-to-end**
  Path: `python3 -m unittest discover -s tests -v`
  Verifies: all unit, integration, e2e, and UI tests across the current
  hierarchical-only streaming system. Current evidence: 250/250 tests green
  with `MODEL_LOAD_LLM=0` on 2026-07-05.

- **`POST /api/v1/meetings/process` end-to-end**
  Path: `tests/integration/test_api_streaming.py`
  Verifies: a request with `flat_texts` materializes into a `DialogueTranscript`
  that respects `MAX_UTTERANCES`, response carries a populated recap, request-id
  is echoed, and empty/invalid payloads return 422 with a `fix` field.

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
