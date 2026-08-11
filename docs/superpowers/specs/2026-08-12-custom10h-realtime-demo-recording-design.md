# Custom_10h Real-Time Web Demo Recording Design

## 1. Objective

Create a reproducible demonstration that sends one hour of `training-eval-suite/data/Custom_10h` audio through the existing web audio pipeline in real time. The web page must visibly receive final ASR utterances, speaker labels, streaming topic/chunk recap events, and the final hierarchical meeting recap. The resulting MP4 must contain the same audible source audio synchronized with the visible transcript.

The demonstration is a separate, explicitly enabled mode. Normal microphone recording and the production `/ws` protocol must continue to behave as they do now.

## 2. Approved Constraints

- The demo contains exactly 3,600 seconds of source timeline audio before finalization.
- WAV files are consumed strictly in physical line order from `recordings.jsonl`.
- A WAV must finish completely before the next WAV begins.
- The player must never randomize, reorder, overlap, or play WAV files concurrently.
- A 0.65-second silent interval separates consecutive utterances so the current 0.5-second Silero silence threshold can finalize the preceding utterance.
- If the next complete WAV plus its required gap would exceed 3,600 seconds, it is not started. The remaining timeline is padded with silence; speech is never truncated to hit the target duration.
- Audio is played and submitted to ASR at 1.0x wall-clock speed.
- The MP4 contains audible meeting audio, not only the web interface.
- After the one-hour timeline finishes, recording continues for at most 90 seconds while the WebSocket session closes and the final recap appears. The resulting video can therefore be slightly longer than one hour.
- Transcript and recap text must be produced by the real backend. Ground-truth supervision text must not be injected into the UI.

## 3. Chosen Approach

Add a browser demo client that uses the existing `/ws` endpoint. The client fetches the deterministic timeline manifest, decodes one WAV at a time, plays it through Web Audio, and sends the same mono Float32 samples to `/ws` in 100-millisecond frames paced against the audio clock.

This approach exercises the existing WebSocket ingress, audio persistence, resampling, VAD, diarization, Zipformer ASR, incremental topic segmentation, summarization, and frontend event rendering. It avoids a virtual microphone, which would add machine-specific PipeWire configuration, and avoids a backend-only replay path that would bypass frontend transport.

## 4. Data Flow

```text
Custom_10h recordings.jsonl
          |
          v
Deterministic 3,600-second timeline builder
          |
          +------------------------+
          |                        |
          v                        v
Demo manifest API             Timeline WAV artifact
          |                        |
          v                        |
Sequential browser player          |
          |                        |
          +--> audible Web Audio   |
          |                        |
          +--> 100 ms Float32 PCM  |
                    |              |
                    v              |
              existing /ws         |
                    |              |
                    v              |
       ASR + speaker + recap events|
                    |              |
                    v              v
              React web UI     FFmpeg audio input
                    |              |
                    v              |
             Playwright WebM ------+
                            |
                            v
                  synchronized H.264/AAC MP4
```

## 5. Timeline Construction

A focused backend service reads `recordings.jsonl` sequentially without sorting it. Each row must resolve to one existing mono 16 kHz WAV under the configured `Custom_10h` directory. The service validates the one-WAV/one-utterance contract, sample rate, frame count, and declared duration before recording begins.

The builder appends a complete WAV and then 0.65 seconds of zero-valued PCM before considering the next row. It stops before any WAV that would cross the 3,600-second boundary and pads the remaining samples with zero-valued PCM. Timeline arithmetic uses integer sample counts at 16 kHz, so the generated timeline contains exactly 57,600,000 samples.

The saved manifest records the original line number, recording ID, relative WAV path, source sample count, start sample, end sample, and following gap size for every selected utterance. It also records the final padding duration and SHA-256 hashes for `recordings.jsonl` and each selected WAV. These fields make the one-hour run reproducible and prove that playback order was not changed.

The corresponding timeline WAV is written incrementally as PCM 16-bit mono at 16 kHz. It is used only as the recorder's audible post-mux track and evidence artifact. Browser ASR input still comes from the original WAV sequence described by the manifest.

## 6. Demo API and Security Boundary

Demo routes are available only when `DEMO_ENABLED=true`. The recorder starts a dedicated loopback-only server with this setting; the normal application leaves the routes disabled.

The API exposes:

- a manifest endpoint returning the already validated, immutable timeline schedule;
- an audio endpoint keyed by `recording_id`, returning only files in the manifest allowlist;
- a lightweight status endpoint exposing the manifest hash and configured duration for recorder preflight.

The audio endpoint never accepts a filesystem path. Unknown IDs, duplicate IDs, paths outside `Custom_10h`, missing files, changed file sizes, and changed hashes fail explicitly. Demo responses do not expose `.env` values or arbitrary local paths.

## 7. Frontend Demo Mode

The React application enters demo mode only when the URL contains `?demo=custom10h`. It creates a new session titled `Custom_10h · Real-time 1-hour Demo`, shows a `LIVE DEMO · Custom_10h` badge, a one-hour progress indicator, current recording ID, elapsed source time, and WebSocket processing state.

An explicit start button is retained because browsers require a user gesture before audible playback. The Playwright recorder clicks this button automatically. Demo mode does not request microphone permission and does not enumerate or select an audio-input device.

`DemoAudioClient` owns one WebSocket, one `AudioContext`, one sequential queue, and one active WAV. For each manifest entry it:

1. fetches and validates the expected WAV response;
2. decodes it to mono Float32 at 16 kHz;
3. plays the samples audibly;
4. submits the same samples to `/ws` in 1,600-sample frames;
5. waits until all samples finish before emitting the 10,400-sample silent gap;
6. advances to the next manifest entry only after that gap completes.

The next WAV may be prefetched but must not be decoded into the playback graph or transmitted early. At most one current WAV and one prefetched WAV remain resident in browser memory.

The demo sends the existing version-1 `session_start` with a 16 kHz mono source and `null` browser microphone-processing settings. It handles existing utterance, segment, chunk, title, meeting-completed, processing-status, pipeline-error, and session-closed events through the same React state update path as microphone recording.

## 8. Real-Time Pacing and Backpressure

PCM transmission is paced from the `AudioContext` clock rather than a chain of unconstrained `setTimeout` calls. Playback and WebSocket submission share one sample cursor, preventing the visible transcript from running ahead of audible speech.

The client monitors `WebSocket.bufferedAmount`. A short backlog pauses both the `AudioContext` and frame submission, records a timing event, and resumes both from the same sample cursor. A backlog that exceeds the configured maximum duration aborts the demo instead of silently dropping or skipping audio.

The recorder collects actual playback start, pause, resume, timeline-complete, meeting-completed, and session-closed timestamps. If backpressure introduced pauses, the final audio track inserts matching silence at those positions before muxing. This preserves synchronization between what was heard during the run and what appears in the MP4.

Pause and resume controls act on both playback and PCM submission. Stop sends the normal `session_end`, waits for `session_closed`, and retains the backend recording for diagnostics.

## 9. Transcript and Recap Behaviour

No demo-only transcript or summary events are synthesized. Final utterances are emitted only when the current Silero VAD and Zipformer path returns non-empty text. Speaker labels come from the active diarization path.

Each accepted utterance is forwarded to the existing incremental `StreamingOrchestrator`. Topic boundaries close through the current Sliding TextTiling logic. Chunk summaries and titles therefore appear in the right-side recap panel during the hour whenever normal segment boundaries close. At the end of the timeline, the recorder stops the WebSocket session, the orchestrator flushes its tail, and the UI receives the final `meeting-completed` hierarchical recap.

The recorder waits up to 90 seconds after source playback. Success requires both `session_closed` and `meeting-completed`. A timeout is recorded as a failed run even if a partial video exists.

## 10. Automated Recording

A Python recorder command performs preflight, timeline generation, frontend build, server startup, browser recording, and FFmpeg muxing. It launches a fresh FastAPI process on a free loopback port so an unrelated development server cannot contaminate the run. The process receives only the explicit demo environment and current project configuration.

Playwright opens Chromium at 1920 by 1080 pixels and records the page to WebM. The page exposes stable demo state markers for `ready`, `playing`, `finalizing`, `completed`, and `failed`; automation does not depend on arbitrary sleep calls except the real-time audio duration.

The recorder measures the actual browser playback-start timestamp relative to video capture. FFmpeg aligns the generated audio track using that offset, preserves silent pre-roll and recap post-roll, transcodes video to H.264, encodes audio as AAC, and writes an MP4 suitable for ordinary presentation software. The browser also plays the audio locally during recording, but the final MP4 audio comes from the deterministic timeline artifact so screen-capture audio-device configuration cannot affect the result.

The primary command shape is:

```bash
PYTHONPATH="$PWD" .venv/bin/python scripts/record_custom10h_demo.py \
  --duration-seconds 3600 \
  --output outputs/demo/custom10h-realtime-1h.mp4
```

## 11. Artifacts and Observability

Every run uses a unique directory under `outputs/demo/` and retains:

- the selected timeline manifest;
- the deterministic timeline WAV;
- the raw Playwright WebM;
- the final MP4;
- backend stdout/stderr;
- browser console and page-error logs;
- playback/backpressure timing events;
- the retained ASR session WAV and diagnostic JSONL path;
- an FFprobe JSON report describing duration, resolution, codecs, frame rate, and audio stream;
- a run summary with completion state and artifact hashes.

Generated artifacts remain ignored by Git. They contain no credentials. On failure, existing WebM, WAV, logs, and diagnostics remain available, but a publishable final video is rerun from the beginning to keep one continuous backend meeting and recap state.

## 12. Failure Policy

Preflight fails before the one-hour wait when the dataset is missing, the corpus cannot fill the requested timeline, a WAV violates format constraints, the frontend build fails, Chromium or FFmpeg is unavailable, GPU ASR readiness fails, or the output filesystem lacks sufficient free space.

During recording, malformed audio, WebSocket closure, excessive backpressure, pipeline errors, browser crashes, server exits, and finalization timeout mark the run failed. The recorder stops child processes cleanly, retains partial evidence, and never labels an incomplete MP4 successful.

The recorder handles operator interruption by requesting normal session finalization when possible, then closing Chromium and the server. It does not delete partial artifacts.

## 13. Testing Strategy

Implementation follows red-green-refactor cycles. Deterministic unit tests cover physical manifest order, sequential non-overlapping boundaries, 0.65-second gaps, exact 57,600,000-sample duration, no partial final WAV, padding, malformed manifests, WAV metadata mismatch, allowlist lookup, and path traversal rejection.

API integration tests prove demo routes are absent by default, available only when enabled, return the same manifest hash, and never serve audio outside the allowlist. Existing microphone WebSocket tests remain unchanged and must continue to pass.

Frontend browser tests use a short deterministic fixture to prove one active WAV at a time, exact order, no overlap, progress updates, pause/resume cursor preservation, backpressure behaviour, reuse of normal server-event rendering, and normal `session_end` finalization.

A 15-second recorder smoke test runs before the one-hour recording. FFprobe must report a 1920 by 1080 video stream and an audible AAC audio stream. The smoke page must show at least one real final utterance and a final recap after stop. Only after this passes is the full 3,600-second run started.

## 14. Acceptance Criteria

The feature is complete when all of the following are true:

- the saved schedule follows `recordings.jsonl` line order exactly;
- every selected WAV is complete, sequential, and non-overlapping;
- every inter-utterance gap is exactly 10,400 samples, except final padding;
- the source timeline is exactly 57,600,000 samples at 16 kHz;
- browser playback and `/ws` submission use the same sample cursor at 1.0x speed;
- no ground-truth transcript is displayed or sent as an ASR result;
- transcript, speaker, streaming recap, and final hierarchical recap are visible on the recorded page;
- `session_closed` and `meeting-completed` are observed before the recorder succeeds;
- the final MP4 is 1920 by 1080 H.264 with an AAC audio stream synchronized to the visible transcript;
- normal microphone recording behaves identically when demo mode is disabled;
- automated tests and the 15-second real-model video smoke test pass before the one-hour run;
- the final run directory contains the MP4 and all evidence artifacts listed above.

## 15. Non-Goals

This feature does not replace Zipformer, improve ASR accuracy, use supervision text to correct predictions, simulate multiple simultaneous speakers, alter the `Custom_10h` corpus, expose demo routes publicly by default, or redesign the meeting recap algorithms. It does not promise seamless continuation of a partially recorded meeting after a browser or backend crash; failed publishable runs restart from the first scheduled WAV.
