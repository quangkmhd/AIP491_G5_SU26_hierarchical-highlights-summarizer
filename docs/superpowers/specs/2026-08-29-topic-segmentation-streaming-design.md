# Topic Segmentation Streaming Design

## Goal

Convert the live meeting path from periodic HTTP batch summarization to true
utterance-by-utterance topic-segmentation streaming. Each accepted ASR
utterance must update exactly one meeting's TextTiling state immediately, while
topic segments remain delayed until the algorithm has enough lookahead or the
meeting is finalized.

Offline uploads continue to use the existing batch endpoint.

## Current Failure

The Gateway persists and emits each utterance, but waits for 40 utterances
before sending a batch request to the LLM module. This duplicates the
TextTiling window responsibility in the Gateway and prevents the LLM streaming
segmenter from receiving incremental updates.

The LLM WebSocket endpoint also resets a process-wide orchestrator whenever a
client connects. Concurrent meetings therefore share and reset each other's
incremental state.

Finally, TextTiling produces local buffer positions while the summarization
orchestrator sometimes interprets them as external utterance indexes. This is
incorrect when indexes don't start at zero or a session is replayed.

## Algorithm Semantics

`StreamingTextTilingSegmenter.update()` appends one utterance immediately. Its
`window_size=40` controls when a complete analysis window is available; it is
not an ingestion batch size. `stride=5` advances overlapping analysis windows.
For a candidate gap `g`, `lookahead=20` prevents commitment until enough later
utterances exist. A committed boundary `g` means that the segment contains
local positions from the previous boundary plus one through `g`, inclusive.

`flush()` evaluates the remaining tail and always commits the last utterance as
the final boundary. It must run exactly once after all pending audio has been
diarized and transcribed.

The streaming implementation must preserve these invariants:

1. Every non-duplicate utterance is appended exactly once and in ascending
   `utterance_index` order.
2. External indexes are metadata only; segmentation ranges use local buffer
   positions and are translated back to external indexes when events are built.
3. A committed boundary never moves backward and is emitted once per live
   connection.
4. No tail segment is finalized before an explicit finish command.
5. Streaming and batch processing produce equivalent complete segment ranges
   for deterministic fixtures, except where the intentional streaming
   lookahead policy changes candidate selection.

## Architecture

### Gateway `MeetingStreamManager`

Add a deep module at the Gateway-to-LLM seam with this interface:

```python
await manager.publish(session_id, utterance)
await manager.finish(session_id)
await manager.close_all()
```

The implementation owns one session worker and one outbound WebSocket per live
meeting. Each worker has a bounded `asyncio.Queue` and serializes sends, ACKs,
and received summary events. Callers don't manage connections, retries, or
ordering.

On first publish, the worker opens the LLM WebSocket and sends a `start`
message containing `session_id` and meeting metadata. It then sends one
`utterance` message and waits for an `utterance-accepted` ACK carrying the same
external index. Segment-related events are persisted and broadcast through the
existing progress callback mechanism.

If a connection breaks, the worker creates a fresh LLM session and replays all
persisted DB utterances in index order. Replaying from the beginning is chosen
because TextTiling state is in memory and the LLM process may have restarted.
It favors correctness over avoiding repeated inference. Events generated while
rebuilding replace the session's materialized summary rather than append
duplicates.

Only one worker may mutate a session. Different sessions run independently.

### LLM WebSocket Session

Each accepted WebSocket creates its own `StreamingOrchestrator` instance. Model
handles may be shared because they are stateless inference dependencies, but
the tiler, utterance list, segment list, counters, and meeting ID must be
connection-local.

Protocol messages are:

```json
{"type":"start","session_id":"...","meeting_title":"..."}
{"type":"utterance","session_id":"...","index":7,"speaker":"S1","text":"..."}
{"type":"flush","session_id":"..."}
```

Every accepted utterance returns an ACK with `session_id` and `index`.
Duplicate indexes return an ACK without appending again. A lower unseen index or
an index gap returns a protocol error; the Gateway then reconnects and performs
a full ordered replay.

`flush` emits all remaining chunk, segment, and title events followed by one
`meeting-completed` event, then closes the logical session.

### Segment Construction

`_build_segment_events` treats segment ranges as positions into
`_incremental_utterances`. It selects utterances by slicing with local positions
and derives event `utterances_start` / `utterances_end` from the selected
utterances' external indexes. This removes the current mixed position/index
interpretation.

The service must not run model summarization for an empty or already emitted
range. Segment ordering follows committed boundary ordering.

### Gateway Pipeline and Finalization

After each successful DB insert in the live path, the pipeline calls
`MeetingStreamManager.publish`. The periodic 40/30 HTTP batch path is removed
from live processing but retained for offline uploads.

The existing pipeline entry point is split explicitly: offline processing ends
in the HTTP batch summarizer, while live-chunk processing ends in `publish` and
does not mark the meeting completed after each chunk. Live sessions remain
active until finalization begins. The session lifecycle records or enforces the
states `recording`, `finalizing`, `completed`, and `failed`; an audio upload is
accepted only while recording.

Add `POST /api/v1/sessions/{session_id}/finalize`. It stops accepting new audio,
waits for already queued audio jobs, flushes the diarization tail, transcribes
and publishes any final utterances, calls `MeetingStreamManager.finish`, saves
the final summary, and marks the session completed.

The Streamlit Stop button calls this endpoint and displays a finalizing state.
It must not merely toggle local UI state.

## Persistence and Materialized Summary

The utterance table remains the source of truth for reconnect replay. The
Gateway maintains a materialized hierarchical summary per session from LLM
events. Intermediate events may update this representation in memory and DB;
`meeting-completed` replaces it with the authoritative final result.

No TextTiling internal arrays are persisted in this change. Full replay is the
recovery strategy.

## Concurrency and Backpressure

Audio chunks for one session must be processed in submission order. A
session-scoped lock protects utterance index allocation and DB insertion. The
stream worker queue is bounded; when full, `publish` waits rather than dropping
an utterance. Different session locks and workers allow concurrent meetings.

Finalization acquires the session lifecycle lock, rejects later audio uploads,
waits for pending work, and then flushes. Calling finalize again is idempotent
and returns the existing final summary.

## Error Handling

- Empty ASR output produces no streaming message.
- LLM disconnect triggers bounded exponential-backoff reconnect and full DB
  replay.
- Protocol ordering errors trigger the same clean replay.
- If finalization cannot reach the LLM after its retry budget, the session is
  marked failed without deleting utterances; finalization can be retried.
- A failed live summary must not mark successfully stored utterances as lost.
- Shutdown closes workers and WebSockets without implicitly flushing active
  meetings.

## Testing

Tests are written before implementation and cover:

1. Segmenter update consumes one utterance at a time and emits nothing before
   enough evidence exists.
2. Flush commits exactly one final tail boundary and is idempotent at the
   session protocol level.
3. Local segment positions map correctly to external indexes that start at a
   non-zero value.
4. Duplicate utterance indexes are ACKed but not appended.
5. Two WebSocket connections maintain independent TextTiling state.
6. Gateway publishes immediately after each DB insert; one utterance reaches
   the LLM without waiting for 40.
7. Disconnect causes ordered DB replay without logical duplicate utterances.
8. Finalize waits for queued audio, publishes the diarization tail, flushes the
   LLM session, and stores `meeting-completed`.
9. Offline batch summarization continues to work.
10. A deterministic corpus compares final streaming ranges with batch ranges
    and documents any intentional lookahead difference.

## Out of Scope

- Persisting or migrating raw TextTiling internal state.
- Exactly-once delivery across services; the protocol provides at-least-once
  delivery with application-level deduplication.
- Replacing Streamlit or the existing audio transport.
- Changing TextTiling scoring parameters without evidence from a separate
  evaluation dataset.
