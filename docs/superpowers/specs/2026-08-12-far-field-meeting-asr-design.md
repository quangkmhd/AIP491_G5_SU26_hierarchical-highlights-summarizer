# Accuracy-First Far-Field Meeting ASR Design

## 1. Objective

Improve Vietnamese speech recognition for meetings where a laptop with its built-in microphone is placed near the center of a room and participants speak from approximately 1–3 metres away. Recognition quality has priority over latency, while the system must preserve all received audio and provide visible processing status.

The implementation must use the streaming transducer files from `models/Zipformer-SSL-100h`, specifically the matching chunk-32 encoder, decoder, and joiner, together with that directory's token file. Although these files currently produce the same results as `models/Zipformer-30M-RNNT-Streaming-6000h`, model provenance and equivalence are outside this change's scope.

## 2. Current Problems

The current browser capture requests `noiseSuppression: false`, performs a simple averaging downsample in JavaScript, and sends unprocessed Float32 PCM directly to the backend. The backend logs quiet chunks but does not normalize, enhance, or recover them. Silero VAD uses a fixed threshold of 0.5, while the frontend VAD slider changes only local React state and never configures the backend.

The backend also decodes each audio sample twice: once through the continuous stream for partial text and again after VAD closes a segment. Speaker embedding runs synchronously before final ASR. The separate audio-preprocessing and diarization project contains DeepFilterNet, VAD, overlap detection, speaker extraction, and separation components, but none is connected to the active `src` pipeline.

## 3. Chosen Approach

Use an accuracy-first buffered pipeline. The frontend captures stable native-rate audio and the backend retains a recoverable local recording, performs high-quality resampling and enhancement, detects speech, handles speaker identity and overlap, and then decodes finalized speech with `Zipformer-SSL-100h`.

The system will not provide speculative partial transcripts. It will display a processing state and emit only finalized utterances. Removing partial decoding avoids duplicate inference and prevents transient text from being mistaken for the final record.

## 4. Architecture

```text
Built-in laptop microphone
          |
          v
Browser media processing and AudioWorklet
          |
          v
WebSocket audio ingress + local session WAV
          |
          v
Stateful high-quality resampler to 16 kHz mono
          |
          +------------------------------+
          |                              |
          v                              v
DeepFilterNet enhancement          Lightly processed audio
          |                              |
          v                              |
Silero VAD + quality gate                |
          |                              |
          +-------------+----------------+
                        v
          Speaker diarization and overlap routing
                        |
                        v
        One or more speaker-labelled audio streams
                        |
                        v
       Zipformer-SSL-100h chunk-32 final decoding
                        |
                        v
      Transcript event + quality and latency metadata
```

The enhanced branch serves VAD and ASR because they benefit directly from improved signal-to-noise ratio. Speaker processing uses a lighter branch because aggressive denoising can remove voice characteristics needed for stable embeddings. Both branches retain the same timeline so speaker labels and text remain alignable.

## 5. Frontend Capture

The frontend will request `echoCancellation`, `noiseSuppression`, and `autoGainControl` for the selected built-in microphone. These constraints are requests rather than assumptions. After capture begins, the frontend will send the actual `MediaStreamTrack.getSettings()` values and the native sample rate to the backend as session metadata.

An `AudioWorklet` will replace the deprecated `ScriptProcessorNode`. It will forward native-rate Float32 mono frames without the current averaging downsampler. The WebSocket protocol will begin with a versioned session-configuration message containing sample rate, channel count, applied track settings, and the selected processing mode. Subsequent binary messages contain audio frames for that session.

The UI will show distinct states for recording, queued processing, finalizing an utterance, degraded CPU processing, and pipeline failure. VAD and runtime settings shown in the frontend must reflect values acknowledged by the backend; controls that cannot change backend behaviour must not be presented as active controls.

## 6. Backend Audio Ingress and Persistence

Each WebSocket connection owns an audio session. Incoming frames are validated for format, finiteness, ordering, and declared sample rate. Valid frames are appended to a local WAV recording and passed to a stateful resampler. The WAV is the recovery source if inference fails or processing falls behind.

Recordings are stored locally with non-guessable session identifiers. The default retention period is 24 hours. A session can be explicitly retained or deleted immediately at the end of a meeting. Cleanup runs independently of inference and records deletion failures without exposing recording contents.

The ingest path must not silently drop audio under backpressure. Audio already received remains in the session WAV, and processing can catch up or replay from the persisted recording. The server reports queue depth and processing lag to the frontend.

## 7. Resampling and Enhancement

Audio is resampled to mono 16 kHz in the backend using a stateful, band-limited implementation supplied by an established audio library. Chunk boundaries must not reset filter state. The browser's current averaging downsampler is removed.

DeepFilterNet processes 2.5-second chunks with 0.3-second overlap and preserves model state for the duration of the session. Overlap-add reconstruction must avoid discontinuities at chunk edges. Configuration starts with the existing conservative 15 dB attenuation limit and disabled post-filter, but the final choice is benchmark-driven.

Accuracy mode treats a missing DeepFilterNet dependency or model as a startup readiness failure rather than silently bypassing enhancement. Diagnostic endpoints must identify the unavailable component and provide an actionable message.

## 8. VAD and Quality Gate

Silero VAD runs on enhanced 16 kHz audio. The threshold is backend-owned, validated, logged per session, and included in session metadata. Calibration compares thresholds 0.2, 0.35, and 0.5 on the far-field benchmark rather than adopting a value based only on intuition.

The quality gate evaluates speech duration, VAD confidence, RMS, peak level, and clipping. A low-quality segment is not destroyed: its location remains in the session recording and its rejection reason is recorded. At session close, VAD is flushed and the remaining valid tail is processed.

## 9. Speaker Processing

The active one-reference-per-speaker matcher is replaced by the speaker-diarization pipeline already present in `AIP491-G5-Audio-Preprocessing-and-Speaker-Diarization`, after its dependencies and model loading are integrated into the main application environment.

For non-overlapping speech, the speaker embedder compares against a voiceprint pool. Profiles are created or updated only from speech that meets minimum duration and confidence requirements. A profile stores a stable aggregate rather than permanently using the first observed embedding.

For overlapping speech, overlap detection selects target-speaker extraction when suitable known profiles exist and blind source separation during cold start. Each valid separated stream is decoded independently and mapped back to the shared timeline. If overlap processing fails, the system retains the enhanced mixed audio, emits its transcript under `Unknown Speaker`, and records the diarization failure. A diarization error must never erase recognizable speech.

## 10. ASR Decoding

ASR uses `sherpa_onnx.OnlineRecognizer.from_transducer` with the chunk-32 encoder, decoder, and joiner in `models/Zipformer-SSL-100h`, its `tokens.txt`, a 16 kHz sample rate, and 80-dimensional features. The three checkpoint files must be validated as one matching set during startup.

Each finalized speaker-labelled segment is fed to a fresh recognizer stream. The decoder receives 0.4 seconds of zero tail padding, input is marked finished, and decoding continues until no frames remain ready. Only the resulting final text is sent to the client.

The old continuous partial recognizer is removed from the WebSocket path. This prevents duplicate decoding and leaves GPU capacity for enhancement, overlap handling, and final recognition.

## 11. Resource and Failure Policy

The target machine has an NVIDIA GeForce RTX 4060 with approximately 8 GB VRAM, a Ryzen 7 5700X with 16 logical CPUs, and 16 GB system RAM. ONNX Runtime exposes TensorRT, CUDA, and CPU providers. Because summarization models also consume substantial memory, audio models must not assume exclusive GPU ownership.

CUDA is preferred. On CUDA out-of-memory or provider failure, queued audio remains recoverable and inference retries on CPU. The frontend is notified that processing is degraded and may be slower. Repeated component failure marks the session pipeline unhealthy instead of repeatedly retrying without limit.

If the WebSocket disconnects, the server finalizes the WAV safely and retains it for replay. Invalid frames close the connection with a specific protocol error. All errors identify the pipeline stage without logging raw audio or transcript contents at debug level by default.

## 12. Transcript Event Contract

Each finalized utterance event contains:

- stable utterance and session identifiers;
- speaker identifier or `Unknown Speaker`;
- final transcript text;
- start and end timestamps derived from the audio timeline;
- source sample rate and final sample rate;
- RMS, peak, clipping indicator, VAD confidence, and speech duration;
- preprocessing, diarization, ASR, and total processing latency;
- degraded-mode and fallback indicators.

Quality metadata is diagnostic and may be hidden in the normal transcript UI. It remains available for benchmark export and troubleshooting.

## 13. Evaluation Dataset

Create a reproducible benchmark using the target laptop and meeting room. Record the same Vietnamese scripts at 0.5, 1, 2, and 3 metres in a quiet room, with fan noise, and with background speech. Include two-speaker turn-taking and at least one overlapping-speech sample. Store reference transcripts and speaker annotations beside the audio under the project evaluation suite.

Every captured file is replayed unchanged through the current baseline and the proposed pipeline. Evaluation reports word error rate, character error rate, VAD miss rate, speaker consistency/error, clipping, real-time factor, and finalization latency. Model and threshold choices are made from these results.

## 14. Acceptance Criteria

The change is accepted when all of the following hold on the agreed benchmark:

- Far-field WER improves by at least 20 percent relative to the current pipeline.
- VAD-missed utterances decrease by at least 50 percent relative to the current pipeline.
- Near-field WER does not regress by more than 5 percent relative.
- The same participant does not continually receive new speaker IDs during ordinary turn-taking.
- No valid received audio frame is silently dropped under normal operation or processing backpressure.
- On the target RTX 4060, the target final transcript appears within 5–8 seconds after an utterance ends; quality remains the priority if a benchmark-supported setting exceeds this target.
- CUDA failure, dependency failure, malformed frames, disconnect recovery, VAD flush, and diarization fallback have automated coverage.
- Frontend tests prove applied microphone settings are reported, and backend tests prove acknowledged VAD/configuration values are used.

## 15. Implementation Boundaries

This change covers browser capture, transport metadata, local session audio persistence, resampling, DeepFilterNet integration, VAD calibration, integration of the existing diarization pipeline, final ASR with `Zipformer-SSL-100h`, transcript diagnostics, and the far-field evaluation harness.

It does not retrain or replace the selected ASR checkpoint, investigate why two model directories contain equivalent files, redesign meeting summarization, or introduce cloud speech services. Existing unrelated worktree changes remain outside the implementation.

## 16. Delivery Order

Implementation proceeds through measurable seams: first build replayable audio fixtures and a baseline report; then replace capture/resampling; integrate enhancement; calibrate VAD; integrate diarization; switch final decoding to the required model path; update the frontend contract; and finally run end-to-end regression and benchmark evaluation. Each stage must be independently replayable so a regression can be attributed to one pipeline boundary.
