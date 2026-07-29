# Zipformer Finalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve final words in every VAD-delimited Zipformer transcript and reject invalid binary PCM safely.

**Architecture:** `AsrEngine` owns the online-recognizer finalization sequence: append a zero tail, signal end of input, decode pending frames, and obtain the final text. The WebSocket adapter validates raw PCM before handing samples to ASR/VAD; it retains the existing event schema.

**Tech Stack:** Python 3.12, NumPy, sherpa-onnx OnlineRecognizer, FastAPI, pytest/unittest.

## Global Constraints

- Retain the binary WebSocket contract: mono 16-kHz Float32 PCM without a header.
- Append exactly 6,400 Float32 zeros (0.4 seconds at 16 kHz) before finalizing a VAD segment.
- Do not append samples after `OnlineStream.input_finished()`.
- Do not change existing WebSocket event payloads.
- Do not load real ASR models in fast tests.

---

### Task 1: Lock recognizer finalization with a unit test

**Files:**
- Create: `tests/unit/test_asr_engine.py`
- Modify: `src/service/asr_engine.py:130-151`

**Interfaces:**
- Consumes: `AsrEngine.decode_segment(audio: np.ndarray, sample_rate: int = 16000) -> str`
- Produces: A final transcript after a speech waveform, 6,400-sample tail, `input_finished()`, and all ready decode calls.

- [x] **Step 1: Write the failing test**

```python
def test_decode_segment_finalizes_with_float32_zero_tail() -> None:
    engine = object.__new__(AsrEngine)
    engine.asr_engine = FakeRecognizer()
    audio = np.array([0.25, -0.25], dtype=np.float32)

    assert engine.decode_segment(audio) == "final text"
    assert engine.asr_engine.stream.waveforms[0][1] is audio
    tail = engine.asr_engine.stream.waveforms[1][1]
    assert tail.dtype == np.float32
    assert tail.shape == (6400,)
    assert np.count_nonzero(tail) == 0
    assert engine.asr_engine.stream.finished is True
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_asr_engine.py::AsrEngineTests::test_decode_segment_finalizes_with_float32_zero_tail -q`

Expected: FAIL because the current implementation accepts only the speech waveform and never calls `input_finished()`.

- [x] **Step 3: Write minimal implementation**

```python
def decode_segment(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
    stream = self.create_stream()
    self.decode_stream_step(stream, audio, sample_rate)
    stream.accept_waveform(sample_rate, np.zeros(int(sample_rate * 0.4), dtype=np.float32))
    stream.input_finished()
    while self.asr_engine.is_ready(stream):
        self.asr_engine.decode_stream(stream)
    return self._result_text(stream)
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_asr_engine.py -q`

Expected: PASS.

### Task 2: Validate WebSocket PCM before ASR

**Files:**
- Modify: `src/runtime/api.py:1-40, 309-322`
- Modify: `tests/integration/test_api_streaming.py`

**Interfaces:**
- Consumes: `_decode_pcm_float32(payload: bytes) -> np.ndarray`
- Produces: C-contiguous finite Float32 samples, or `ValueError` with a user-actionable explanation.

- [x] **Step 1: Write the failing tests**

```python
def test_decode_pcm_float32_rejects_non_float32_byte_length(self) -> None:
    with self.assertRaisesRegex(ValueError, "multiple of 4"):
        _decode_pcm_float32(b"x")

def test_decode_pcm_float32_rejects_non_finite_samples(self) -> None:
    with self.assertRaisesRegex(ValueError, "finite"):
        _decode_pcm_float32(np.array([np.nan], dtype=np.float32).tobytes())
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_api_streaming.py::PcmValidationTests -q`

Expected: FAIL because `_decode_pcm_float32` does not exist.

- [x] **Step 3: Write minimal implementation and route integration**

```python
def _decode_pcm_float32(payload: bytes) -> np.ndarray:
    if len(payload) % np.dtype(np.float32).itemsize:
        raise ValueError("audio frame byte length must be a multiple of 4 for Float32 PCM")
    chunk = np.frombuffer(payload, dtype=np.float32)
    if not np.isfinite(chunk).all():
        raise ValueError("audio frame must contain only finite Float32 PCM samples")
    return chunk
```

The WebSocket route catches this `ValueError`, logs the rejection, and closes
with code 1003 without forwarding invalid audio to VAD or ASR.

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_api_streaming.py -q`

Expected: PASS.

### Task 3: Run regression and real runtime verification

**Files:**
- Modify: `docs/QUALITY_SCORE.md`

- [x] **Step 1: Run focused tests**

Run: `uv run pytest tests/unit/test_asr_engine.py tests/integration/test_api_streaming.py -q`

Expected: PASS.

- [x] **Step 2: Run full fast suite**

Run: `uv run pytest tests/ -q`

Expected: PASS with no new failures.

- [x] **Step 3: Run live diagnostic**

Run:

```bash
LD_LIBRARY_PATH=.venv/lib/python3.12/site-packages/onnxruntime/capi:$LD_LIBRARY_PATH \
uv run python -c 'from src.service.asr_engine import AsrEngine; print(type(AsrEngine()).__name__)'
```

Expected: `AsrEngine` prints after loading the configured CUDA Zipformer.

- [x] **Step 4: Record evidence**

Add an ASR + Speaker entry to `docs/QUALITY_SCORE.md` with the focused test,
full-suite result, runtime model-load result, and the remaining limitation that
no Vietnamese ground-truth audio fixture exists yet.
