# Streaming Hierarchical Recap — Design Spec

**Date:** 2026-07-05
**Status:** Approved (pending written review)
**Area:** `types`, `config`, `service`, `runtime`, `ui`, `evaluation`
**Layer position:** `Types -> Config -> Repo -> Service -> Runtime -> UI`
**Related specs:**

- `docs/superpowers/specs/2026-07-04-model-002-design.md` (Approved) — CoherenceNet + ModelLoader (CoherenceNet no longer used by segmentation; see D4 note)
- `docs/superpowers/specs/2026-07-05-config-001-centralized-config-design.md` (Approved) — `MeetingRecapConfig` + 5 sub-configs

---

## 0. Context

This spec captures four decisions made on 2026-07-05 that re-shape the
project's product surface and pipeline design:

1. **DR1 (Highlights) is dropped from scope.** The product now ships the
   _Hierarchical_ recap only. Rationale: paper-2 §3.1 positions the two
   recap types as complementary, but the user requested implementing
   only the Hierarchical method (`hierarchical_segment` + `hierarchical_abstractive`
   - `hierarchical_title`) and explicitly excluded the highlights
     extractive model.
 2. **Topic segmentation uses lexical Sliding TextTiling.** The pipeline
    was rewritten to use a purely lexical BoW + cosine similarity +
    multi-scale depth scoring approach, removing the NSP-BERT CoherenceScorer.
    This method computes depth scores at multiple peak-search radii
    (default `[3, 5, 10, 15, 20]`), normalises each via z-score,
    aggregates them (mean), then thresholds at `mean + alpha * std`.
    No neural scoring model is required, making segmentation fast and
    deterministic without GPU dependencies.
3. **End-to-end streaming pipeline (C3).** The recap is delivered as a
   stream of incremental state events over Server-Sent Events (HTTP) or
   NDJSON (CLI). The orchestrator is an async generator that emits
   chapter cards as soon as TextTiling confirms a boundary, before the
   deBERTa summary / title model returns. This matches paper-2 §5.3.1's
   finding that users adopt a breadth-first exploration strategy
   (chapter heading first, then chunks, then raw transcript) and that
   skeleton states during inference latency are acceptable (paper-2
   §5.3.2: participants edited chapter titles confidently even when
   summaries were still generating).
4. **No 4-bit gemma-4-E2B-it-qat-GGUF LLM at MVP.** `MockLLMBackbone` (already in
   `src/repo/model_loader.py`) provides canned Vietnamese responses for
   the deBERTa-based summarization tasks (`segment`, `abstractive`,
   `title`). The real `Viet-Mistral/gemma-4-E2B-it-qat-GGUF` load is deferred
   behind `MODEL_LOAD_LLM=1` (already supported in `model-002`).
   Rationale: paper-2 uses deBERTa for `hierarchical_abstractive` and
   `hierarchical_title`, not a generative LLM; the only LLM-shaped
   component in the pipeline is the deBERTa encoder for chunk
   summarization, which can be mocked at MVP.

The four decisions collectively reduce `feature_list.json` from 17
features to 12 features (3 patches to existing features, 3 merges into
gated service/runtime/ui features, 1 feature dropped, 1 evaluation
feature re-scoped).

---

## 1. Goals (acceptance targets)

After this spec lands and all 12 features pass:

- A user pastes a Vietnamese meeting transcript and clicks "Process".
  Within 3 minutes the Web prototype shows all chapter cards with
  titles and chunk summaries, with at least 1 card visible within the
  first 5 seconds (proves streaming is wired, not polling).
- The chapter boundaries produced on the
  `data/eval_vi/meeting_committee.json` sample (370 utterances, 8
  ground-truth segments) match paper-1 quality: median absolute
  boundary offset ≤ 2 utterances from ground truth on at least 5 of
  the 8 segments.
- The pipeline runs offline (no network calls after the one-time
  checkpoint load). All five AI model artifacts are local.
- The user can edit a chapter title inline and the override persists
  in the recap JSON via `PATCH /api/v1/meetings/{id}/segments/{idx}/title`.
- The user can copy a chapter or chunk to the clipboard, and can
  reveal up to 3 surrounding transcript utterances via a "Show
  context" affordance (paper-2 §3.4).
- `python -m src.runtime.cli stream <file.json>` runs the same pipeline
  from the command line and prints NDJSON events to stdout.
- `feature_list.json` has 12 features (3 patches, 3 merged
  service/runtime/ui, 1 dropped, 1 re-scoped evaluation); all are
  `passing` or `blocked` with a documented blocker.

---

## 2. Patches to existing features (D-series decisions)

### D1. `model-001+` — Remove Highlights data models

The product no longer ships Highlights. Drop from the Types layer:

- `src/types/highlight.py` — deleted.
- `src/types/hierarchical_recap.py::HierarchicalRecap` — fields
  `highlights_notes: list[Highlight]` and
  `highlights_tasks: list[Highlight]` removed.
- `src/types/__init__.py` — re-exports of `Highlight`, `HighlightType`,
  `HighlightSource` removed.
- `tests/unit/test_types.py` — the 5-7 existing tests that exercise
  Highlight / HighlightType / HighlightSource /
  `HierarchicalRecap.highlights_*` are deleted (or rewritten to assert
  the fields no longer exist).
- `tests/manual/test_meeting_committee_sample.py` — 370-utterance
  round-trip still produces a valid `HierarchicalRecap` with only
  `segments`, `meeting_id`, `generated_at`, `processing_time_ms`,
  `status`.

**Acceptance:** `python3 -m unittest discover -s tests -v` is green
after the deletion. Expected count: 144 (current) − ~7 (highlight
tests) − ~5 (highlights config tests via D2) = ~132 tests.

### D2. `config-001+` — Drop `HighlightsConfig` from `MeetingRecapConfig`

`HighlightsConfig` only existed to feed `svc-005` (highlights
pipeline), which is dropped. With the consumer gone, the config is
dead code.

- `src/config/highlights.py` — deleted.
- `src/config/recap.py::MeetingRecapConfig` — field
  `highlights: HighlightsConfig = Field(default_factory=...)` removed.
- `src/config/__init__.py` — `HighlightsConfig` removed from re-exports.
- `tests/unit/test_config_highlights.py` — deleted.
- `tests/unit/test_config_recap.py` — `HIGHLIGHTS__*` env-var test
  cases removed; `MeetingRecapConfig` now composes 4 sub-configs
  (`TextTilingConfig`, `ChunkingConfig`, `AbstractiveConfig`,
  `LanguageConfig`).
- `src/config/README.md` — `MEETING_RECAP_HIGHLIGHTS__*` env-var row
  deleted from the env-var table.

**Acceptance:** `python3 -m unittest discover -s tests -v` is green
after the deletion. `docs/QUALITY_SCORE.md` Config layer note adds:
"HighlightsConfig was removed in 2026-07-05 because the highlights
pipeline is out of scope per design decision."

### D3. `eval-002` — Re-scope harness to streaming UX only

The original `eval-002` (in `feature_list.json`) was a user-study
harness comparing _highlights vs hierarchical_ recaps. With DR1
dropped, the comparison axis is gone.

New `eval-002` scope:

- A manual harness that runs a small-N user study (target N=7 like
  paper-2 §4) with the Hierarchical streaming prototype only.
- Captures per-participant ratings for:
  1. **Time-to-first-chapter** (seconds, from SSE connection open to
     first `segment-closed` event received in browser).
  2. **Comfort with skeleton state** (1-5 Likert).
  3. **Discoverability of Copy + Show-Context** (1-5 Likert).
  4. **Overall streaming UX score** (1-5 Likert).
- Output: a streaming-UX report at
  `docs/generated/streaming-ux-report.md` with N=7 participant rows
  and aggregate stats. The report has no "highlights" column.

**Acceptance:** the harness script exists; running it on a synthetic
participant (no real humans) produces a report with the 4 metrics and
the right shape.

---

## 3. New / merged features

### D4. `svc-001+002` — Topic Segmentation Pipeline (Sliding TextTiling)

**Components:**

- `src/segmenters/sliding_texttiling.py` — core algorithm functions:
  - `bow(utterance, stopwords) -> dict[str, int]` — tokenises by
    lowercasing, stripping punctuation, and filtering Vietnamese stop
    words.
  - `similarity_scores(utterances, block_size, stopwords) -> list[float]`
    — computes cosine similarity between BoW vectors at every
    consecutive gap, pooling each side into a `block_size` window.
  - `depth_scores(scores, radius) -> list[float]` — classic TextTiling
    depth formula: `0.5 * (left_peak + right_peak - 2 * score[i])`
    within a search radius.
  - `multiscale_depth(scores, radii, normalize, agg) -> list[float]`
    — runs depth scoring at multiple radii, normalises each profile
    (z-score or minmax), and aggregates (mean/max/sum) into a single
    multi-scale depth profile.
  - `find_boundaries(scores, radii, alpha, normalize, agg, min_segment_ratio)`
    — end-to-end: multiscale depth → threshold (mean + alpha * std)
    → candidate boundaries → merge small segments.
  - `merge_small_segments(boundaries, depths, n_utterances, min_ratio)`
    — greedy merge of segments below `min_ratio * n_utterances` into
    the shallower-depth neighbour.
- `src/service/text_tiling.py` — `SlidingTextTilingService` class:
  - `process(utterances: list[str]) -> list[SegmentEvent]` — consumes
    utterance strings directly (no external scorer), calls
    `find_boundaries()`, and emits `SegmentEvent` dataclass instances.
  - Stateless and reusable across calls; loads Vietnamese stopwords
    via `stopwordsiso` on first use when `use_stopwords=True`.

**Pipeline (per-call):**

1. BoW every utterance.
2. Cosine similarity at every gap with `block_size` pooling.
3. Multi-scale depth: run depth scoring per radius, z-score, aggregate.
4. Threshold: `mean + alpha * std`.
5. Merge segments smaller than `min_segment_ratio`.
6. Emit `SegmentEvent`s.

**Key difference from the original paper-1 approach:** no neural
coherence scoring model is used. The pipeline is purely lexical,
GPU-free, and deterministic.

**Verification block:**

- `test_sliding_text_tiling.py`:
  - `bow` returns correct token counts, filters stopwords.
  - `similarity_scores` returns values in [-1, 1] with correct length.
  - `depth_scores` identifies valleys on synthetic similarity data.
  - `multiscale_depth` produces fewer distinct values than input
    length (proves aggregation happened).
  - `find_boundaries` returns empty list on flat similarity (no
    boundaries), non-empty on valley-rich input.
  - `merge_small_segments` consolidates tiny segments.
  - `SlidingTextTilingService.process` returns `SegmentEvent`s with
    unique IDs, non-overlapping ranges covering `[0, n)`.

### D5. `svc-006+streaming` — Streaming Orchestrator

`src/service/meeting_recap_orchestrator.py` — `StreamingOrchestrator`
class.

**Event types emitted by `process_stream(transcript_iterator)`:**

| Event                 | Payload                                                                   | Trigger                                              |
| --------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------- |
| `utterance-accepted`  | `{index, speaker, text}`                                                  | every new utterance after the first                  |
| `depth-score-updated` | `{window_idx, depth_score, pair: [utt_i, utt_i+1]}`                       | new depth score from SlidingTextTilingService         |
| `segment-closed`      | `{segment_id, utterances_start, utterances_end, depth_score_at_boundary}` | `depth_score > τ` (TextTiling cutoff crossed)        |
| `chunk-closed`        | `{chunk_id, segment_id, rolling_summary}`                                 | chunk fills to 8 utt OR segment closes               |
| `title-emitted`       | `{segment_id, title}`                                                     | segment closes; `hierarchical_title` deBERTa returns |
| `meeting-completed`   | `{hierarchical_recap: HierarchicalRecap}`                                 | transcript iterator exhausted                        |

**Ordering guarantees (for client and tests):**

- `utterance-accepted[i]` fires before `depth-score-updated[i-1]`.
- `segment-closed` fires at most once per `segment_id`.
- `title-emitted` for segment N never fires before
  `segment-closed[N]` and never after `meeting-completed`.
- `meeting-completed` is the last event in every successful run.

**Deferred title inference (UX-critical) — the only deferred target:**

The slowest operation is deBERTa inference per segment title
(~100-500 ms per inference on GPU). To keep the stream flowing:

1. On `segment-closed`, the orchestrator immediately emits the event.
2. `hierarchical_title` is scheduled as a background `asyncio` task.
3. When the task returns, `title-emitted` is emitted (may arrive many
   events later, e.g. after the next segment closes).
4. The UI interprets "segment card without title" as a skeleton state
   (pulsing gray bar) until `title-emitted` lands.

**Chunk summaries (rolling_summary in chunk-closed) are synchronous
at MVP.** The deBERTa call for a single chunk (~100-500 ms) is
acceptable to block the orchestrator on because the next event is
either another `utterance-accepted` (depth score still
accumulating) or another `chunk-closed` for the next chunk in the
same segment. If the real deBERTa is later swapped in and chunk
inference exceeds ~1 s, the spec can be re-scoped to make chunk
summaries deferred too; for MVP the MockLLMBackbone returns in <1 ms
so the synchronous path is fine.

This pattern matches paper-2 §5.3.1: participants expanded chapter
cards first, then explored chunks inside them, then transcripts. A
skeleton chapter card with placeholder title "Chapter N" is
sufficient to anchor exploration; the title upgrades in place.

**Batch entry point retained:**

`StreamingOrchestrator.process_batch(transcript) -> HierarchicalRecap`
remains for offline CLI use and for the
`tests/manual/test_meeting_committee_sample.py` regression test. The
batch path is implemented as
`[event async-iter → final HierarchicalRecap]`.

**Verification block:**

- `test_orchestrator_streaming.py`:
  - `process_stream` on a 100-utterance fixture yields the 6 event
    types in the documented order; `meeting-completed` is the last
    event.
  - The final `HierarchicalRecap` from `process_stream` equals the
    one from `process_batch` on the same input (byte-for-byte JSON
    equality).
  - `process_stream` never emits `title-emitted` for a segment that is
    later re-opened.
  - `processing_time_ms` ∈ [0, 180_000] (3-minute budget from
    RELIABILITY.md).

### D6. `runtime-001+002+streaming` — Runtime Surfaces (FastAPI SSE + CLI stream)

`src/runtime/api.py` and `src/runtime/cli.py` — see ARCHITECTURE.md
Service Map for the module names.

**FastAPI route:**

```
POST /api/v1/meetings/stream
  Content-Type: application/json
  Body: TranscriptIngestionRequest
  Response: text/event-stream (Server-Sent Events)
```

Each SSE event is formatted as:

```
event: <event-type>
data: <json-payload>

```

The final `meeting-completed` event is followed by a special
`event: end` / `data: {}` marker so clients know the stream is done.

Why SSE, not WebSocket: SSE is HTTP (works through corporate
proxies), has built-in reconnect via `EventSource`, and is sufficient
because the recap is unidirectional (server → client). The orchestrator
is streaming-capable regardless of transport, so a future WebSocket
route for live ASR is a no-op in the orchestrator.

**CLI subcommand:**

```
python -m src.runtime.cli stream <transcript.json>
```

Reads the JSON file, runs `StreamingOrchestrator.process_stream`,
prints events to stdout in NDJSON (one event per line, no framing).
The `--output <path>` flag persists the final `HierarchicalRecap` to
`RecapRepo`.

**Batch endpoints (retained for backward compat with `model-001`):**

```
POST /api/v1/meetings/process   # returns full HierarchicalRecap JSON
GET  /api/v1/meetings/{id}      # retrieve persisted recap
GET  /api/v1/meetings           # list meetings
PATCH /api/v1/meetings/{id}/segments/{idx}/title   # chapter title override
```

**Verification block:**

- `test_api_streaming.py` (FastAPI `TestClient`):
  - `POST /api/v1/meetings/stream` returns
    `Content-Type: text/event-stream` within 1 second of request
    start.
  - The first event for a 100-utterance input is
    `utterance-accepted`.
  - `meeting-completed` is the last event and is followed by the
    `end` marker.
  - Closing the SSE connection mid-stream stops the orchestrator
    without leaking GPU memory (verified by
    `torch.cuda.memory_allocated()` snapshot before/after).
- `test_cli_streaming.py` (subprocess):
  - `python -m src.runtime.cli stream data/eval_vi/meeting_committee.json`
    exits 0 and prints ≥ 1 `segment-closed` line per ground-truth
    segment (8 for the committee sample).
  - With `--output /tmp/recap.json`, the file is written and matches
    the final `meeting-completed` payload.

### D7. `ui-001+002+streaming` — Web Prototype (Hierarchical tab with streaming)

`src/ui/index.html`, `src/ui/app.js`, `src/ui/styles.css` — single-page
HTML prototype. The page has one tab ("Hierarchical"). There is no
"Highlights" tab; the paper-2 DR1 surface is dropped from the product
per D1.

**User flow:**

1. User pastes a transcript and clicks "Process".
2. The page opens an `EventSource` to
   `POST /api/v1/meetings/stream` (via `fetch` + `ReadableStream` —
   the browser SSE API doesn't accept POST bodies, so the page
   `fetch`es the route and reads the response body as an SSE stream).
3. On every `segment-closed` event, the page appends a chapter card
   with a placeholder title "Chapter N" and a pulsing skeleton bar
   for the title only (chunk summaries arrive in their `chunk-closed`
   events as final text, no skeleton needed — see D5).
4. On `title-emitted`, the placeholder title is replaced in place.
5. On every `chunk-closed` event, the card's chunk list is extended.
   The `rolling_summary` field in the event payload is the final
   text (deBERTa inference is synchronous for chunk summaries at MVP
   per D5; segment titles are the only deferred inference target).
   The UI does not show a skeleton for chunk summaries.
6. On `meeting-completed`, the page hides the "processing" indicator
   and finalizes the card grid.

**Card affordances (per chapter card):**

- **Copy button** — copies the chapter title + the joined chunk
  summaries to the clipboard via `navigator.clipboard.writeText`.
- **Show-Context link** — for each chunk summary, a "Show context"
  link that reveals up to 3 transcript utterances before and 3
  after the chunk's `utterances_start` / `utterances_end` (paper-2
  §3.4 spec, enforced to 3 on each side per the paper text).
- **Inline title edit** — click the title to enter edit mode; blur
  fires `PATCH /api/v1/meetings/{id}/segments/{idx}/title` with the
  new value.

**Visual:**

- Skeleton state: a 1.2 s linear pulse on a gray bar
  (`@keyframes pulse { 0% { opacity: 0.6 } 50% { opacity: 1.0 } 100% { opacity: 0.6 } }`).
- Card grid: 1 column on viewports < 768 px, 2 columns on ≥ 768 px.
  Per FRONTEND.md §"UI Principles" (clarity over novelty).

**Verification block:**

- `tests/ui/test_prototype_streaming.py` (Playwright headless):
  - Load `src/ui/index.html` in headless Chromium; paste a
    100-utterance transcript fixture; click "Process".
  - Assert: at least 1 chapter card is present in the DOM within
    5 seconds (proves streaming is wired, not polling).
  - Assert: the page has no "Highlights" tab (proves DR1 is dropped
    from the UI surface).
  - Assert: every chapter card has a Copy button and a Show-Context
    link.
  - Assert: clicking Show-Context on a chunk reveals exactly 3
    surrounding transcript utterances.
  - Assert: clicking Copy triggers a `navigator.clipboard.writeText`
    call (verified by reading the `clipboard-write` permission mock).

---

## 4. The dropped feature

### D8. `svc-005` — Highlights pipeline (DELETED)

`svc-005` (Highlights Pipeline — extractive BART + abstractive
deBERTa) is removed from `feature_list.json`. Rationale captured at
D1/D2: highlights are out of product scope.

If a future milestone wants highlights back, it would be a new
feature (`svc-008-highlights-pipeline`, priority ≥ 18) — not a
re-activation of `svc-005`.

---

## 5. Files changed

### New (12)

| Path                                                                       | Purpose                                                                                                    |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `src/segmenters/sliding_texttiling.py`                                     | Core Sliding TextTiling algorithm (BoW, cosine, depth, multiscale, merge) (D4)                               |
| `src/service/text_tiling.py`                                               | `TextTilingService` with sliding-window + depth-score cutoffs (D4)                                         |
| `src/service/chunking_service.py`                                          | `ChunkingService` for 8-utterance chunks (D5)                                                              |
| `src/service/hierarchical_summarization.py`                                | `HierarchicalSummarizationService` (deBERTa title + abstractive, mocked via `MockLLMBackbone` at MVP) (D5) |
| `src/service/meeting_recap_orchestrator.py`                                | `StreamingOrchestrator` (D5)                                                                               |
| `src/runtime/api.py`                                                       | FastAPI + sse-starlette (D6)                                                                               |
| `src/runtime/cli.py`                                                       | argparse with subcommand `stream` (D6)                                                                     |
| `src/ui/index.html`                                                        | Single-page prototype shell (D7)                                                                           |
| `src/ui/app.js`                                                            | EventSource client, in-place DOM updates (D7)                                                              |
| `src/ui/styles.css`                                                        | Card grid + skeleton pulse (D7)                                                                            |
| `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md` | This spec                                                                                                  |
| `docs/exec-plans/active/<feat>-<slug>.md`                                  | One per new feature (7 plans)                                                                              |

### Modified (17)

| Path                                            | Change                                                                                                                                |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `src/types/hierarchical_recap.py`               | Drop `highlights_notes`, `highlights_tasks` (D1)                                                                                      |
| `src/types/__init__.py`                         | Drop Highlight re-exports (D1)                                                                                                        |
| `src/config/recap.py`                           | Drop `highlights` field (D2)                                                                                                          |
| `src/config/__init__.py`                        | Drop HighlightsConfig re-export (D2)                                                                                                  |
| `src/config/README.md`                          | Drop HIGHLIGHTS\_\_\* env-var row (D2)                                                                                                |
| `tests/unit/test_types.py`                      | Drop highlight cases; assert no `highlights_*` fields (D1)                                                                            |
| `tests/unit/test_config_recap.py`               | Drop HIGHLIGHTS\_\_\* env-var tests (D2)                                                                                              |
| `tests/manual/test_meeting_committee_sample.py` | Recap round-trip without highlights (D1)                                                                                              |
| `docs/design-docs/system-architecture.md`       | Update container diagram (drop BART highlights; add SSE) (D5-D7)                                                                      |
| `docs/design-docs/paper-integration.md`         | Rewrite: only paper-1 _Ours (full)_ + paper-2 _Hierarchical_; drop DR1 references (D1, D4)                                            |
| `docs/design-docs/models-and-roadmap.md`        | Drop AI Models §2.2 highlights entry; update pipeline description (D1)                                                                |
| `docs/FRONTEND.md`                              | Drop "Highlights view" surface (D7)                                                                                                   |
| `docs/PRODUCT_SENSE.md`                         | Rewrite "Job to be done", "Quality bar", "UX Vocabulary" (no more `Highlight` enum) (D1)                                              |
| `docs/RELIABILITY.md`                           | Add "End-to-end streaming golden journey" + 3-min budget (D5, D6)                                                                     |
| `docs/QUALITY_SCORE.md`                         | Update snapshot: drop Highlights & Action Items row; add "Streaming UX" row (D3)                                                      |
| `ARCHITECTURE.md`                               | Update Service Map: drop `HighlightsService`; rename orchestrator to `StreamingOrchestrator`; add SSE cross-cutting interface (D4-D7) |
| `feature_list.json`                             | Replace 17 features with 11 per the new schema (D1-D8)                                                                                |
| `pyproject.toml`                                | Add `sse-starlette` and `playwright` (test-only) (D6, D7)                                                                             |

### Deleted (5)

| Path                                                 | Reason                                                             |
| ---------------------------------------------------- | ------------------------------------------------------------------ |
| `src/types/highlight.py`                             | DR1 dropped (D1)                                                   |
| `src/config/highlights.py`                           | DR1 dropped (D2)                                                   |
| `tests/unit/test_config_highlights.py`               | DR1 dropped (D2)                                                   |
| `src/repo/prompts_vi.py::HIGH_PROMPTS["highlights"]` | DR1 dropped; keep `segment` / `abstractive` / `title` prompts (D4) |
| `docs/exec-plans/active/svc-005-*.md` (if any)       | DR1 dropped (D8)                                                   |

### Untouched

- `src/repo/coherence_net.py` — `CoherenceNet` loads from the
  checkpoint but is **not used by the current segmentation pipeline**
  (topic segmentation uses lexical Sliding TextTiling instead).
- `src/repo/model_loader.py` — `ModelLoader` supports `ModelKind.NSP`
  with `bert-base-multilingual-cased` + `vibert_checkpoints_vi/cpt_4000.pth`
  (smoke loader green), but the NSP path is only loaded if explicitly
  requested; the orchestrator no longer calls it.
- `src/repo/transcript_repo.py`, `src/repo/recap_repo.py` — file IO
  paths unchanged; `RecapRepo` is shared between the streaming and
  batch paths.
- `src/types/_base.py` — shared base schema unchanged.
- The two Approved specs (`model-002`, `config-001`) — referenced but
  not modified.

---

## 6. Streaming event contract (canonical)

This is the source of truth for client and tests. Every event has the
shape `{"event": <type>, "data": <payload>}` on the wire. CLI NDJSON
uses `{"type": <type>, "payload": <payload>}` per line (no framing).

```jsonc
// 1. utterance-accepted
{
  "event": "utterance-accepted",
  "data": {
    "index": 12,             // 0-based, matches DialogueTranscript.utterances[i].index
    "speaker": "S3",
    "text": "Tôi đồng ý với đề xuất này."
  }
}

// 2. depth-score-updated
{
  "event": "depth-score-updated",
  "data": {
    "window_idx": 7,         // sliding window position
    "depth_score": 0.18,     // 0.5 * (left_flag + right_flag - 2 * score[i])
    "pair": [                // for Show-Context affordance
      "Vâng, tôi sẽ gửi báo cáo.",
      "Cảm ơn anh. Tôi sẽ chuẩn bị slide cho cuộc họp sau."
    ]
  }
}

// 3. segment-closed
{
  "event": "segment-closed",
  "data": {
    "segment_id": "seg-3",
    "utterances_start": 24,
    "utterances_end": 41,
    "depth_score_at_boundary": 0.34   // the depth_score that crossed τ
  }
}

// 4. chunk-closed
{
  "event": "chunk-closed",
  "data": {
    "chunk_id": "seg-3-chunk-2",
    "segment_id": "seg-3",
    "utterances_start": 32,
    "utterances_end": 39,
    "rolling_summary": "Nhóm thảo luận về tiến độ dự án và phân công nhiệm vụ tuần tới."  // Vietnamese 3rd-person
  }
}

// 5. title-emitted
{
  "event": "title-emitted",
  "data": {
    "segment_id": "seg-3",
    "title": "Phân công nhiệm vụ tuần tới"
  }
}

// 6. meeting-completed
{
  "event": "meeting-completed",
  "data": {
    "hierarchical_recap": { /* HierarchicalRecap JSON */ }
  }
}

// 7. end (SSE terminator)
{
  "event": "end",
  "data": {}
}
```

**Wire format constraints:**

- All events are JSON; no binary frames.
- Event types are lowercase-hyphenated strings, exactly matching the
  table above.
- The orchestrator is responsible for assigning `segment_id` (string,
  starts with `seg-`) and `chunk_id` (`seg-N-chunk-M`); clients MUST
  NOT infer IDs from numeric position.
- The `meeting-completed` payload is the full `HierarchicalRecap`
  serialized via `model_dump(mode="json")` (UUIDs as strings,
  datetimes as ISO-8601), so a client that only listens for
  `meeting-completed` can render the whole recap in one shot.

---

## 7. Test plan (consolidated)

| Test file                                                 | Layer         | Coverage                                                                        | Min tests    |
| --------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------- | ------------ |
| `tests/unit/test_sliding_text_tiling.py`                  | service       | bow, cosine, depth, multiscale, boundaries, merge, service process              | 10           |
| `tests/unit/test_text_tiling.py`                          | service       | depth_score formula, cutoff_threshold, sliding window, boundary count, coverage | 8            |
| `tests/unit/test_chunking_service.py`                     | service       | 8-utt chunks, overlap semantics, oversize handling                              | 4            |
| `tests/unit/test_hierarchical_summarization.py`           | service       | title and abstractive mocked via `MockLLMBackbone`; output shape                | 4            |
| `tests/unit/test_orchestrator_streaming.py`               | service       | event ordering, batch-streaming equality, no double-close, time budget          | 6            |
| `tests/unit/test_types.py` (UPDATED)                      | types         | drop highlight cases; assert no `highlights_*` fields                           | ~31 (was 38) |
| `tests/unit/test_config_recap.py` (UPDATED)               | config        | drop HIGHLIGHTS env-var tests; 4-sub-config composition                         | ~10 (was 12) |
| `tests/integration/test_api_streaming.py`                 | runtime       | SSE event order, end marker, CUDA leak check                                    | 5            |
| `tests/integration/test_cli_streaming.py`                 | runtime       | NDJSON, exit 0, output file matches                                             | 3            |
| `tests/ui/test_prototype_streaming.py`                    | ui            | Playwright: card within 5 s, no Highlights tab, copy, show-context, skeleton    | 6            |
| `tests/manual/test_streaming_committee_sample.py`         | end-to-end    | 370-utterance committee → 8 cards stream in, JSON-equal to batch path           | 1            |
| `tests/manual/test_meeting_committee_sample.py` (UPDATED) | end-to-end    | Recap round-trip without highlights fields                                      | 1 (existing) |
| `tests/manual/test_streaming_ux_harness.py`               | evaluation    | Synthetic participant run; report shape                                         | 1            |
| `tests/unit/test_layer_rule_*.py` (existing)              | cross-cutting | AST scans; no cross-layer imports introduced                                    | 3 (existing) |
| **Total new**                                             |               |                                                                                 | ~50          |
| **Total after all migrations**                            |               |                                                                                 | **~136**     |

---

## 8. Verification commands

```bash
# 1. Static layer rules
python3 -m unittest discover -s tests/unit -p "test_layer_rule_*.py" -v

# 2. Unit suite (regression + new service / type / config)
python3 -m unittest discover -s tests/unit -v

# 3. Integration suite (API + CLI)
python3 -m unittest discover -s tests/integration -v

# 4. UI suite (Playwright headless)
python3 -m unittest discover -s tests/ui -v

# 5. End-to-end manual smoke (370-utterance committee, streaming)
python3 tests/manual/test_streaming_committee_sample.py
python3 tests/manual/test_meeting_committee_sample.py   # batch path, regression

# 6. End-to-end manual smoke (config layer)
python3 tests/manual/test_config_end_to_end.py

# 7. UX harness (synthetic participant)
python3 tests/manual/test_streaming_ux_harness.py

# 8. Full suite (one-shot)
python3 -m unittest discover -s tests -v
```

Definition of Done for the whole spec: commands 1, 2, 3, 4, 5, 6, 7, 8
all green; `progress.md` records a Session 004+ entry with the
verification run output; `docs/QUALITY_SCORE.md` updated with the
post-spec snapshot.

---

## 9. Risks

- **R1 — `cpt_4000.pth` is a partial-training checkpoint.** The
  training log shows only 4,000 steps of Epoch 1 / 10. Validation
  accuracy at step 4,000 is 0.7752 (F1 ≈ 0.78), which is in the
  ballpark of paper-1 Table 4 (F1=0.776 for `Ours (full)` on
  DialSeg_711). If the user wants paper-grade numbers, an
  additional 6 epochs of fine-tuning is required. **Mitigation:**
  the spec does not block on paper-grade F1; the acceptance
  criterion (D1 verification) is "at least 1 segment-closed event
  on the 100-utterance fixture". Future plan
  `svc-009-extended-finetune` can resume training if needed.
- **R2 — SSE may not work through all corporate proxies.** The
  1-second header response and small event sizes are proxy-friendly.
  Fallback for hostile networks: a `POST /api/v1/meetings/process`
  batch endpoint already exists for `model-001` regression; the
  orchestrator can also be polled via
  `GET /api/v1/meetings/{id}` (the recap is persisted to `RecapRepo`
  on `meeting-completed` regardless of transport).
- **R3 — Skeleton state UX may confuse users.** Paper-2 §5.3.2 found
  participants were comfortable editing chapter titles even when
  summaries were still generating. Risk: if the deBERTa mock is
  replaced with a real model and inference exceeds ~3 s per chunk,
  the UX degrades. **Mitigation:** a 3 s `processing_time_ms` budget
  is documented in `RELIABILITY.md`; if exceeded, the spec ships
  anyway but the UX test is marked as needing follow-up.
- **R4 — Lexical segmentation accuracy on real meetings.** The
  Sliding TextTiling method uses BoW + cosine similarity, which may
  miss topic boundaries that depend on semantic understanding (e.g.,
  same vocabulary used in different topic contexts). **Mitigation:**
  the `eval-001` (P_k, Win-Diff, F1) feature is preserved and will
  surface the actual score; `progress.md` records the achieved
  number so future agents can plan improvements.
- **R5 — The 17 → 12 feature reduction is a one-way door for the
  current milestone.** Highlights code paths are deleted (D1, D2,
  D8). If a future milestone wants highlights back, it must be a
  new feature with new evidence. **Mitigation:** the
  `merged_from` / `patch_of` / `dropped_from` fields in
  `feature_list.json` retain the lineage so the reversal cost is
  visible.

---

## 10. Out of scope (deferred to future specs)

- **Live ASR ingestion via WebSocket** — the orchestrator is
  streaming-capable but the runtime surface is HTTP+SSE only.
- **Multi-speaker voice separation** — assumed to be solved upstream
  by the ASR system; we accept a `DialogueTranscript` with stable
  `speaker` labels.
- **Chapter annotation (user-marked key-points within a chapter)**
  — would require a new `Annotation` data model and a new event
  type; deferred.
- **Slide / chat cross-references in the recap** — paper-2 §6
  limitation; deferred.
- **Cross-meeting recap linking** — "the same topic appeared in
  yesterday's meeting" — not in either paper; deferred.
- **Real gemma-4-E2B-it-qat-GGUF deBERTa-replacement inference** — gated by
  `MODEL_LOAD_LLM=1` (already supported in `model-002`); can be
  enabled in `svc-004` future work without changing the event
  contract.

---

## 11. Definition of Done

The spec is "done" when:

- All 12 features in `feature_list.json` are `passing` (or `blocked`
  with a documented blocker).
- `python3 -m unittest discover -s tests -v` is green; total test
  count is in the 130-140 range.
- `docs/QUALITY_SCORE.md` snapshot row for "2026-07-05" shows:
  - Topic Segmentation: C → B
  - Hierarchical Recap: C → B
  - CLI App: D → B
  - Highlights & Action Items: row removed
  - Streaming UX: row added (eval-002 result)
- `progress.md` records a Session 004+ entry with the verification
  run output.
- `docs/exec-plans/active/` has exactly 7 active plans, one per
  `not_started` feature in the new `feature_list.json` (the 4
  already-passing features are not in `active/`).
- The 370-utterance committee sample streams end-to-end in under 3
  minutes (RELIABILITY.md budget) and the final `HierarchicalRecap`
  is JSON-equal between the streaming and batch paths.
- The repository can restart cleanly from the standard startup path
  (`uv sync` → `python3 -m unittest discover -s tests -v`).
