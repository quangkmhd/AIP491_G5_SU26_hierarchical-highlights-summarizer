# Topic Segmentation Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver each live ASR utterance immediately to an isolated LLM TextTiling stream and finalize its tail reliably when the meeting stops.

**Architecture:** The LLM WebSocket creates one stateful orchestrator per connection. The Gateway owns a `MeetingStreamManager` whose per-session worker serializes messages, consumes ACK and summary events, and replays persisted utterances after reconnect. Offline uploads keep the HTTP batch path; live chunks publish incrementally and use an explicit finalize endpoint.

**Tech Stack:** Python 3.12, FastAPI, asyncio, websockets asyncio client, SQLite, pytest/unittest fakes

**Spec:** `docs/superpowers/specs/2026-08-29-topic-segmentation-streaming-design.md`

## Global Constraints

- Every live utterance is ingested once in ascending external `utterance_index` order.
- TextTiling ranges are local buffer positions; emitted segment metadata uses external indexes.
- `window_size=40` remains inside TextTiling and is never a Gateway batching threshold.
- Recovery is at-least-once transport with full ordered DB replay and LLM-side deduplication.
- Offline batch behavior remains available.
- Existing untracked virtual environments and DB journal files aren't modified.

---

### Task 1: Correct Local Position and External Index Semantics

**Files:**
- Modify: `backend/llms-module/service/summarization_orchestrator.py`
- Create: `backend/llms-module/tests/test_streaming_orchestrator.py`

**Interfaces:**
- Consumes: `MultiscaleTextTilingService.update(text) -> list[tuple[int, int]]`
- Produces: `StreamingOrchestrator.accept_utterance(text, speaker, index)` events whose segment ranges expose external utterance indexes.

- [ ] **Step 1: Write failing tests** using a fake tiler returning local range `(0, 1)` for utterances with external indexes `10` and `11`; assert the emitted segment starts at `10`, ends at `11`, and contains exactly those two utterances. Add a flush-twice test asserting the second flush produces no events.
- [ ] **Step 2: Run** `PYTHONPATH=backend/llms-module pytest -q backend/llms-module/tests/test_streaming_orchestrator.py` and confirm the non-zero-index test fails.
- [ ] **Step 3: Implement** positional slicing in `_build_segment_events`, derive metadata from `segment_utts[0].index` and `segment_utts[-1].index`, and track finalized state so repeated flush is empty.
- [ ] **Step 4: Re-run the focused test** and confirm it passes.
- [ ] **Step 5: Commit** `test(llm): lock streaming segment index semantics`.

### Task 2: Isolate and Validate LLM WebSocket Sessions

**Files:**
- Modify: `backend/llms-module/runtime/api.py`
- Create: `backend/llms-module/runtime/stream_protocol.py`
- Create: `backend/llms-module/tests/test_streaming_api.py`

**Interfaces:**
- Consumes: an orchestrator factory `Callable[[], StreamingOrchestrator]` stored on app state.
- Produces: protocol handler accepting `start`, ordered `utterance`, and `flush`; ACKs contain `session_id`, `index`, and optional `duplicate`.

- [ ] **Step 1: Write failing tests** with FastAPI `TestClient.websocket_connect`: two connections send different sessions without resetting each other; duplicate index is ACKed with `duplicate=true`; a gap returns `type=error`; flush returns one `meeting-completed`.
- [ ] **Step 2: Run** `PYTHONPATH=backend/llms-module pytest -q backend/llms-module/tests/test_streaming_api.py` and confirm shared-state/protocol tests fail.
- [ ] **Step 3: Implement** a connection-local `StreamProtocolSession` holding `session_id`, expected index, accepted index set, and its own orchestrator. Construct it per WebSocket; share only model-backed summarizer dependencies when safe.
- [ ] **Step 4: Re-run Tasks 1–2 tests** and confirm they pass.
- [ ] **Step 5: Commit** `feat(llm): isolate streaming topic sessions`.

### Task 3: Add the Gateway Meeting Stream Manager

**Files:**
- Create: `backend/services/meeting_stream_manager.py`
- Create: `backend/tests/test_meeting_stream_manager.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: DB methods `get_session`, `get_utterances`, `save_summary`; LLM events from `ws://localhost:8003/ws`.
- Produces: `publish(session_id: str, utterance: dict, progress_callback=None)`, `finish(session_id: str, progress_callback=None) -> dict | None`, and `close_all() -> None`.

- [ ] **Step 1: Write failing async tests** with a fake WebSocket connector: one publish sends `start` then exactly one utterance and waits for matching ACK; two sessions have independent connections; a broken connection reconnects and replays DB utterances in order; finish sends flush and stores `meeting-completed`.
- [ ] **Step 2: Run** `pytest -q backend/tests/test_meeting_stream_manager.py` and confirm the missing module fails.
- [ ] **Step 3: Implement** one session state containing `asyncio.Lock`, connection, acknowledged index, and closed flag. Keep the public interface small; serialize publish/receive under the session lock, use bounded exponential backoff, full DB replay on a fresh connection, and route summary events through the callback.
- [ ] **Step 4: Re-run the focused tests** and confirm they pass.
- [ ] **Step 5: Commit** `feat(gateway): add per-meeting LLM streams`.

### Task 4: Split Offline Batch and Live Incremental Pipeline Paths

**Files:**
- Modify: `backend/services/pipeline_orchestrator.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_live_pipeline_streaming.py`

**Interfaces:**
- Consumes: `MeetingStreamManager.publish`, `finish`, `close_all`.
- Produces: `process_live_audio_chunk(...)` that persists and publishes immediately; existing `process_audio_file(...)` remains the offline batch path; `finalize_live_session(...)` flushes SD then finishes LLM.

- [ ] **Step 1: Write failing tests** proving one routed utterance invokes `publish` without an LLM HTTP batch call, live processing doesn't mark the session completed per chunk, and finalization publishes flushed utterances before calling `finish`.
- [ ] **Step 2: Run** `pytest -q backend/tests/test_live_pipeline_streaming.py` and confirm current threshold behavior fails.
- [ ] **Step 3: Extract** shared diarization/transcription persistence into private helpers, then implement distinct offline and live entry points. Allocate indexes under a per-session lock and track pending live jobs for finalize.
- [ ] **Step 4: Wire** the manager in `backend/main.py` and close it during lifespan shutdown.
- [ ] **Step 5: Re-run Gateway tests** and confirm they pass.
- [ ] **Step 6: Commit** `refactor(gateway): stream live utterances immediately`.

### Task 5: Add Explicit Idempotent Finalization

**Files:**
- Modify: `backend/db/schema.sql`
- Modify: `backend/db/database.py`
- Modify: `backend/api/sessions.py`
- Create: `backend/tests/test_live_session_api.py`

**Interfaces:**
- Consumes: `PipelineOrchestrator.process_live_audio_chunk` and `finalize_live_session`.
- Produces: `POST /api/v1/sessions/{session_id}/finalize`; live lifecycle values `recording`, `finalizing`, `completed`, `failed`.

- [ ] **Step 1: Write failing API/DB tests** asserting online session creation starts as `recording`, audio is rejected after finalizing, finalize is idempotent, and the final summary is returned.
- [ ] **Step 2: Run** `pytest -q backend/tests/test_live_session_api.py` and confirm schema/endpoint failures.
- [ ] **Step 3: Implement** a forward-compatible SQLite status migration by rebuilding or relaxing the status constraint safely for existing databases; add a conditional status transition method so only `recording -> finalizing` wins.
- [ ] **Step 4: Change** the audio endpoint to queue the live entry point and register pending work; add finalize endpoint that waits for it and calls the finalizer.
- [ ] **Step 5: Run focused DB/API tests** and confirm they pass.
- [ ] **Step 6: Commit** `feat(api): finalize live meetings safely`.

### Task 6: Connect the Streamlit Stop Control

**Files:**
- Modify: `frontend_streamlit/app.py`
- Create: `backend/tests/test_frontend_finalize_contract.py`

**Interfaces:**
- Consumes: `POST /api/v1/sessions/{session_id}/finalize`.
- Produces: Stop UI that waits for backend finalization before setting the meeting inactive.

- [ ] **Step 1: Write a source-contract test** asserting the Stop branch posts to the session finalize URL before setting `live_meeting_active=False`.
- [ ] **Step 2: Run** `pytest -q backend/tests/test_frontend_finalize_contract.py` and confirm it fails.
- [ ] **Step 3: Implement** the finalize request with a visible spinner, success/error handling, and no local stop transition on failure.
- [ ] **Step 4: Run the focused test** and confirm it passes.
- [ ] **Step 5: Commit** `fix(ui): finalize streaming meeting on stop`.

### Task 7: Verify Algorithm Equivalence and Full Regression Suite

**Files:**
- Create: `backend/llms-module/tests/test_streaming_batch_equivalence.py`
- Modify: `backend/llms-module/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: public batch and streaming orchestrator interfaces.
- Produces: deterministic evidence and documented live protocol.

- [ ] **Step 1: Add a deterministic multi-topic fixture** and compare complete batch ranges with update-plus-flush ranges; where lookahead intentionally differs, assert monotonic non-overlapping coverage and document the exact difference.
- [ ] **Step 2: Run** `PYTHONPATH=backend/llms-module pytest -q backend/llms-module/tests/test_streaming_batch_equivalence.py` and inspect the initial verdict before changing algorithm parameters.
- [ ] **Step 3: Fix only proven streaming algorithm defects**; don't tune `alpha`, radii, window size, stride, or lookahead without evaluation evidence.
- [ ] **Step 4: Document** start/utterance/ACK/flush messages, reconnect replay, and the finalize endpoint.
- [ ] **Step 5: Run** `pytest -q backend/tests` and `PYTHONPATH=backend/llms-module pytest -q backend/llms-module/tests`.
- [ ] **Step 6: Run** `python -m compileall -q backend frontend_streamlit` and `git diff --check`.
- [ ] **Step 7: Commit** `test: verify end-to-end topic streaming`.
