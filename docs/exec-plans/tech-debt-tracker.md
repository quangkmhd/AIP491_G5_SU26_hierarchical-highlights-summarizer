# Tech Debt Tracker

This file tracks deferred work and follow-ups that are out of scope for
the current active plan. Items here are non-blocking for shipping the
current milestone but should be addressed before the next major one.

## Severity Legend

- **Important** -- affects correctness, performance, or UX in a way users
  can notice.
- **Minor** -- cleanup, polish, or documentation that improves legibility
  but does not change observable behavior.

## Open Items

### Minor (from model-001 self-review, 2026-07-04)

- **No `__all__` in `src/types/schemas.py`**
  - File: `src/types/schemas.py`
  - Issue: `__init__.py` already names the three classes explicitly, so
    this is fine, but a local `__all__` would tighten the module's
    public surface.
  - Fix: add `__all__ = ["TranscriptIngestionRequest", "HighlightUpsertRequest", "MeetingProcessResponse"]`.
  - Owner: next agent touching `schemas.py`.

- **No `repr` customization for large models**
  - File: `src/types/transcript.py`, `src/types/hierarchical_recap.py`
  - Issue: Pydantic's default repr prints every utterance, which is
    noisy for a 370-utterance transcript.
  - Fix: add `__repr_args__` that limits nested repr depth, or set
    `model_config = ConfigDict(repr=False)` for these two models.
  - Owner: next agent touching debugging UX.

- **Deterministic UUID in demo is undocumented**
  - File: `tests/manual/test_meeting_committee_sample.py`
  - Issue: the demo uses `UUID(int=(dial_id + 1) * 10**12)` so the
    output JSON is reproducible. Production code uses `uuid4()`.
  - Fix: a one-line comment explaining "deterministic for diffable demo
    output" so the next reader doesn't think the production code is
    supposed to be deterministic.
  - Owner: next agent touching the smoke test.

- **No `to_compact_dict()` helper on `HierarchicalRecap`**
  - File: `src/types/hierarchical_recap.py`
  - Issue: `model_dump_json()` includes the full `Chunk.utterances` text,
    which is 243 KB for the Vietnamese committee meeting. The recap
    payload the UI needs is just metadata (segment ranges, titles, rolling
    summaries, highlights) -- the raw utterances already live in the
    source transcript.
  - Fix: add a `to_compact_dict()` method that drops `chunks[].utterances`
    and includes only `chunks[].chunk_id` + `chunks[].rolling_summary`.
  - Owner: next agent implementing `api-001`.

## Resolved Items

(none yet)
