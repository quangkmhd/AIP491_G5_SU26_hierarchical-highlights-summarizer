# Runtime Layer

This directory is the entry point of the application execution.

## Role
- Orchestrates and bootstraps the application.
- Houses executable scripts, Command Line Interfaces (CLIs), background workers, or API route handlers (e.g. FastAPI app).
- Handles user argument parsing and presents the outputs.

## Rules
- **Dependency Limit**: Can import from any layer (`service`, `repo`, `config`, `types`) to bootstrap the workflow.
- Avoid placing core algorithm or ML logic directly in this layer; delegate all heavy lifting to the `service` layer.

## Core Modules to Implement
- `cli.py`: CLI application taking transcript files, executing segmentation and recap tasks, and formatting output for stdout/files.

## Far-Field WebSocket Audio

Start the runtime with the application factory so model initialization occurs once during server startup:

```bash
uvicorn src.runtime.api:create_app --factory --host 0.0.0.0 --port 8005
```

The `/ws` endpoint uses protocol version 1. Its first message must be a JSON `session_start` containing the native microphone sample rate, mono channel count, and browser-applied echo-cancellation, noise-suppression, and automatic-gain settings. Subsequent binary messages are mono Float32 PCM at that native rate.

Each connection persists its source PCM as a native-rate FLOAT WAV, resamples continuously to 16 kHz with high-quality SoXR, applies Silero VAD, assigns stable speaker profiles, and performs one finalized Zipformer decode per speech segment. Browser-processed PCM is preserved by default because applying DeepFilterNet after browser noise suppression removed recognizable distant speech in the captured-room replay. DeepFilterNet remains available with `ASR_DENOISER_ENABLED=true` for separately validated noisy environments.

The default ASR checkpoint is `models/Zipformer-SSL-100h`. Far-field-sensitive VAD uses threshold `0.25`, minimum speech `0.25` seconds, minimum silence `0.5` seconds, and maximum speech `10.0` seconds.

The client must send `{"type":"session_end","retain":true}` and wait for `session_closed`. If a connection disappears unexpectedly, the server still flushes and retains valid received audio. Retained recordings are cleaned after 24 hours by default.

Every production session writes `<session-id>.diagnostics.jsonl` beside its WAV. After reproducing weak capture, inspect the latest session with:

```bash
PYTHONPATH="$PWD" .venv/bin/python -m src.runtime.audio_diagnostics
```

The `suspected_stage` field distinguishes `capture_or_transport`, `capture`, `preprocessing`, `vad`, and `asr`. The same report includes browser microphone settings, source and processed RMS, clipping, detected speech duration, ASR empty-result rate, and whether the session closed cleanly. To inspect a specific session, pass its diagnostics path as the positional argument.

Run focused verification with:

```bash
RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/unit/test_audio_types.py \
  tests/unit/test_audio_capture.py \
  tests/unit/test_audio_preprocessor.py \
  tests/unit/test_audio_diagnostics.py \
  tests/unit/test_session_diagnostics.py \
  tests/unit/test_diarization_engine.py \
  tests/unit/test_asr_engine.py \
  tests/unit/test_far_field_pipeline.py \
  tests/integration/test_api_streaming.py \
  tests/e2e/test_far_field_audio_replay.py -q
```

## Custom_10h Real-Time Demo Recording

The recorder enables demo-only routes on an isolated loopback server, plays WAV rows in physical `recordings.jsonl` order, and sends the same audible 16 kHz PCM through `/ws` at 1.0x speed. It records a 1920×1080 browser WebM, renders the deterministic playback WAV, and muxes an H.264/AAC MP4. Demo routes remain disabled during normal server startup.

Run a short real-model smoke before committing an hour to the recording:

```bash
LD_LIBRARY_PATH="$PWD/.venv/lib/python3.12/site-packages/onnxruntime/capi:$PWD/.venv/lib/python3.12/site-packages/sherpa_onnx/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
PYTHONPATH="$PWD" .venv/bin/python scripts/record_custom10h_demo.py \
  --duration-seconds 15 \
  --output outputs/demo/custom10h-smoke-15s.mp4
```

Record the requested one-hour source timeline without acceleration:

```bash
LD_LIBRARY_PATH="$PWD/.venv/lib/python3.12/site-packages/onnxruntime/capi:$PWD/.venv/lib/python3.12/site-packages/sherpa_onnx/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
PYTHONPATH="$PWD" .venv/bin/python scripts/record_custom10h_demo.py \
  --duration-seconds 3600 \
  --output outputs/demo/custom10h-realtime-1h.mp4
```

Keep at least 8 GiB free. Each run creates a timestamped evidence directory beside the MP4 containing the raw WebM, timeline WAV, ordered manifest, browser/backend logs, browser trace, FFprobe JSON, and `run-summary.json` hashes. An interrupted or failed run keeps every partial artifact for diagnosis; it never reports success without `meeting-completed`, `session_closed`, and valid H.264/AAC streams.
