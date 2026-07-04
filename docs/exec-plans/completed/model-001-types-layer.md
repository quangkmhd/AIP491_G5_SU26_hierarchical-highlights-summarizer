# model-001 — Types Layer (COMPLETED 2026-07-04)

## Objective

Define the core Pydantic v2 data models that every other layer will exchange
through, with strict validation, predictable JSON serialization, and clean
separation between domain types and API request/response schemas.

## Scope

- Pydantic v2 models for `Utterance`, `DialogueTranscript`, `Chunk`,
  `SegmentResult`, `Highlight`, `HierarchicalRecap`, plus the enums
  `HighlightType`, `HighlightSource`, `MeetingStatus`.
- API request/response schemas: `TranscriptIngestionRequest`,
  `HighlightUpsertRequest`, `MeetingProcessResponse`.
- A shared `BaseSchema` to centralize the strictness rules
  (`extra="forbid"`, `populate_by_name`, `str_strip_whitespace`).
- 38 unit tests covering valid construction, validation failures, immutability,
  ClassVar constants, UX alias classmethods, JSON wire format, and a real
  370-utterance Vietnamese committee round-trip.
- A runnable smoke test that loads the first dialogue from
  `data/eval_vi/meeting_committee.json` and writes a `HierarchicalRecap`
  JSON to `docs/generated/model001_demo_recap.json`.

## Out of Scope

- HuggingFace model loading (covered by `model-002`).
- TextTiling / summarization / orchestration (covered by `svc-001`, `svc-002`).
- FastAPI runtime (covered by `api-001`).
- UI work (covered by `ui-001`).

## Verification Path

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
python3 -m unittest discover -s tests -v
# Expected: Ran 38 tests in ~0.1s -- OK

python3 tests/manual/test_meeting_committee_sample.py
# Expected: 8 segments, 50 chunks, 1 note, 1 task, JSON written.
```

The layer rule is mechanically checked inside the smoke test
(`tests/manual/test_meeting_committee_sample.py`): an AST scan
confirms `src/types/*.py` has zero imports from `config`/`repo`/
`service`/`runtime`.

## Risks and Blockers

None. The biggest risk was that the data model would be re-shaped by the
service layer later; mitigated by routing everything through Pydantic from
day 1.

## Progress Log

### 2026-07-04 (session 001)

- Implemented all 11 Pydantic models + `BaseSchema` in `src/types/`.
- Wrote `tests/unit/test_types.py` with 30 tests, all green.
- Wrote `tests/manual/test_meeting_committee_sample.py` (initially
  `demo_model001.py` in `src/types/`; later moved to `tests/manual/` and
  renamed to decouple from the feature id).
- Generated `docs/generated/model001_demo_recap.json` (243 KB) from the
  first Vietnamese committee meeting.

### 2026-07-04 (session 001, post-review)

A self code review found 3 Important issues; all fixed in the same session:

1. `TranscriptIngestionRequest` did not reject an empty payload -- added a
   `model_validator` requiring at least one of `utterances`/`flat_texts`.
2. `materialize()` did not re-check `MAX_UTTERANCES` -- added explicit
   size check with a clear error message.
3. `DialogueTranscript.MAX_UTTERANCES = 5000` was a documented constant
   with no enforcement -- folded into the existing `_validate_transcript`
   `model_validator`.

Plus a JSON wire-format test for `HighlightType` (locks the canonical
"key_point" / "action_item" values; UX-friendly `note()` / `task()`
classmethods are tested to produce the same wire value).

Test count: 30 -> 38 (one was a duplicate alias test that was redundant with the wire-format test).

## Open Decisions

None. All decisions are recorded in `docs/design-docs/DESIGN.md` (Recently
Settled Decisions section) and the relevant field docstrings.

## Verification at Archive Time

```text
$ python3 -m unittest discover -s tests -v
... Ran 39 tests in 0.138s -- OK

$ python3 tests/manual/test_meeting_committee_sample.py
meeting_id     : 00000000-0000-0000-0000-00e8d4a51000
meeting_title  : Committee Meeting 0
segments       : 8
total_chunks   : 50
highlights     : notes=1 tasks=1
first segment  : 'Chapter 1' (13 utts, 2 chunks)
first chunk    : 8 utts
wrote         : docs/generated/model001_demo_recap.json
```

`feature_list.json::model-001.status = "passing"`.
`docs/QUALITY_SCORE.md` updated; Types layer grade: C -> B.
