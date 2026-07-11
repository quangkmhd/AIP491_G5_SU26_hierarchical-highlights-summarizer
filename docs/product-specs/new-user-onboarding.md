# New User Onboarding

## Goal

A new user pastes a meeting transcript, sees a hierarchical recap within
the synchronous budget (3 minutes for <= 5,000 utterances), and is
convinced that the recap captures the meeting's structure correctly
enough to act on.

## Entry Conditions

- The user has a meeting transcript available as plain text or as a
  sequence of utterances with speaker labels.
- The user is using the Web App (`ui-001`, not yet implemented) **or**
  the Python CLI / `uv run src/runtime/cli.py` (depends on `api-001`).
- The system requires the local ViT5 chunk summarizer and BARTpho topic
  titler on CUDA. Topic segmentation uses lexical Sliding
  TextTiling — no neural checkpoint required for segmentation.

## User Flow

1. The user opens the Web App or CLI.
2. The user pastes the transcript (or a JSON file with `utterances_vi` /
   `utterances_en`).
3. The user clicks "Process" (Web) or runs `process-meeting <file>` (CLI).
4. The client `POST /api/v1/meetings/process` with a
   `TranscriptIngestionRequest` payload (either `utterances` or
   `flat_texts`).
5. The server:
   - Calls `TranscriptIngestionRequest.materialize()` to build a
     `DialogueTranscript`. Empty payloads and payloads over
     `MAX_UTTERANCES = 5000` are rejected here with a clear error.
   - Runs `SlidingTextTilingService` to split the transcript into `SegmentResult`s.
   - Chunks each segment into <= 8-utterance `Chunk`s.
   - Summarizes each chunk with ViT5, then gives only the ordered completed
     summaries in that topic to BARTpho to generate its title.
   - Returns a `HierarchicalRecap` in the response body.
6. The client renders the recap. The hierarchical view shows chapters in
   chronological order.

## Acceptance Criteria

- A user submitting the first dialogue in
  `data/eval_vi/meeting_committee.json` (370 utterances, 8 ground-truth
  segments) receives a `HierarchicalRecap` with:
  - 8 segments matching the ground-truth segment lengths
    (currently verified structurally via
    `tests/manual/test_meeting_committee_sample.py`).
  - 50 chunks (each <= 8 utterances, since long segments must be split).
  - 1+ key-point highlights and 1+ action-item highlights.
- The `POST /api/v1/meetings/process` request returns HTTP 200 with
  `status = "completed"` and a populated `recap` field. (TBD with
  `api-001`.)
- A request with an empty payload returns HTTP 422 with a body that
  mentions "at least one of `utterances` or `flat_texts`". (Already
  verified at the schema level by
  `test_request_rejects_empty_payload`.)
- A request with a payload over 5,000 utterances returns HTTP 422 with
  a body that mentions `MAX_UTTERANCES`. (Already verified at the
  schema level by `test_materialize_rejects_oversized_flat_texts`.)
- A user can rename a chapter title and re-fetch the recap to see the
  override (depends on `ui-001` + `api-001`).

## Failure States

- Empty payload: 422 with a clear "at least one of" error.
- Over-sized payload: 422 with the actual size and the 5,000 cap.
- Transcript with non-contiguous utterance indices: 422 with the
  offending indices.
- Transcript with a JSON key not declared in the schema: 422 with
  the extra field name.
- Model loading failure: HTTP 503 (Service Unavailable) with
  `error = "ModelLoader: <reason>"`. The recap JSON is `null`.
- Processing failure mid-pipeline: `HierarchicalRecap.status = FAILED`
  with `error` populated; the user sees a "Try again" button.

## Recovery

- Failed jobs can be retried by re-submitting the same
  `TranscriptIngestionRequest`. The `transcript_id` is stable for a
  given request, so the retry hits the same on-disk file path.
- If the model is unloaded between requests, the `ModelLoader`
  re-loads it on first use; no manual intervention required.
