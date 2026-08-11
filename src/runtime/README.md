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

Each connection persists its source PCM as a native-rate FLOAT WAV, resamples continuously to 16 kHz with high-quality SoXR, enhances 2.5-second windows with DeepFilterNet, applies Silero VAD, assigns stable speaker profiles, and performs one finalized Zipformer decode per speech segment. The default ASR checkpoint is `models/Zipformer-SSL-100h`, and the default VAD threshold is `0.35` for far-field sensitivity.

The client must send `{"type":"session_end","retain":true}` and wait for `session_closed`. If a connection disappears unexpectedly, the server still flushes and retains valid received audio. Retained recordings are cleaned after 24 hours by default.

Run focused verification with:

```bash
RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/unit/test_audio_types.py \
  tests/unit/test_audio_capture.py \
  tests/unit/test_audio_preprocessor.py \
  tests/unit/test_diarization_engine.py \
  tests/unit/test_asr_engine.py \
  tests/unit/test_far_field_pipeline.py \
  tests/integration/test_api_streaming.py \
  tests/e2e/test_far_field_audio_replay.py -q
```
