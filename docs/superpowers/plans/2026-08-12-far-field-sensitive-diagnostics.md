# Far-Field Sensitive Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve recognizable distant speech by removing default double denoising and emit inspectable per-session diagnostics.

**Architecture:** The default factory selects an explicit pass-through enhancer while retaining DeepFilterNet behind configuration. A focused JSONL diagnostic writer receives lifecycle and signal events from `FarFieldSession` without owning audio processing.

**Tech Stack:** Python 3.12, NumPy, SoundFile, SoXR, sherpa-onnx, Pydantic Settings, pytest.

## Global Constraints

- Use `models/Zipformer-SSL-100h` without changing checkpoint files.
- Default VAD values are threshold `0.25`, minimum speech `0.25`, minimum silence `0.5`, and maximum speech `10.0` seconds.
- DeepFilterNet remains available only when `ASR_DENOISER_ENABLED=true`.
- Diagnostics never contain PCM samples, credentials, or serialized environment values.
- Preserve all unrelated user modifications.

---

### Task 1: Sensitive Defaults and Explicit Denoiser Selection

**Files:**
- Modify: `src/config/asr.py`
- Modify: `src/service/audio_preprocessor.py`
- Modify: `src/runtime/api.py`
- Test: `tests/unit/test_asr_engine.py`
- Test: `tests/unit/test_audio_preprocessor.py`

**Interfaces:**
- Produces: `AsrConfig.denoiser_enabled: bool` and `PassthroughEnhancer.enhance(samples) -> np.ndarray`.
- Consumes: existing `Enhancer` and `DefaultFarFieldSessionFactory` boundaries.

- [ ] Write tests asserting the four sensitive VAD defaults and duration-preserving pass-through output.
- [ ] Run the focused tests and confirm failures against the current `0.35/0.5/0.25/5.0` configuration and missing enhancer.
- [ ] Implement the defaults, enhancer, and explicit runtime selection.
- [ ] Run focused tests and commit.

### Task 2: Recoverable Session Diagnostics

**Files:**
- Create: `src/service/session_diagnostics.py`
- Modify: `src/service/far_field_pipeline.py`
- Modify: `src/service/audio_capture.py`
- Test: `tests/unit/test_session_diagnostics.py`
- Modify: `tests/unit/test_far_field_pipeline.py`
- Modify: `tests/unit/test_audio_capture.py`

**Interfaces:**
- Produces: `SessionDiagnostics.record(event: str, **fields)`, `close(**fields)`, and `NullSessionDiagnostics`.
- Consumes: session start metadata, source frames, processed chunks, VAD segments, ASR results, and close state.

- [ ] Write failing tests for JSONL lifecycle records, empty ASR visibility, and paired cleanup.
- [ ] Run focused tests and confirm failure because diagnostics do not exist.
- [ ] Implement best-effort JSONL writing and inject it into each factory-created session.
- [ ] Run focused tests and commit.

### Task 3: Real Recording Replay and Complete Verification

**Files:**
- Modify: `src/runtime/README.md`
- Modify: `docs/generated/far-field-asr-acceptance.md`

**Interfaces:**
- Consumes: retained WAV and JSONL diagnostic output.
- Produces: reproducible inspection commands and measured before/after replay counts.

- [ ] Replay the latest retained WAV with real models and record non-empty utterance/word counts.
- [ ] Run `RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest tests -q`.
- [ ] Run frontend build/lint and legacy-path scans.
- [ ] Document how to locate the latest diagnostics and commit.
