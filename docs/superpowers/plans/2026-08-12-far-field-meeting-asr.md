# Far-Field Meeting ASR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an accuracy-first, replayable far-field meeting audio pipeline for the laptop microphone that produces finalized Vietnamese transcripts with stable speaker labels using `models/Zipformer-SSL-100h`.

**Architecture:** The browser sends native-rate Float32 PCM and negotiated microphone metadata through a versioned WebSocket protocol. The backend persists the source audio, performs stateful high-quality resampling, enhancement, VAD, diarization, and one final ASR decode per speaker-labelled segment. Each boundary exposes deterministic fixtures and metrics so quality regressions can be attributed to capture, enhancement, VAD, speaker processing, or ASR.

**Tech Stack:** React 19, TypeScript 6, Web Audio `AudioWorklet`, FastAPI WebSockets, NumPy, SoundFile, soxr, DeepFilterNet, sherpa-onnx, ONNX Runtime CUDA, pytest.

## Global Constraints

- Use `models/Zipformer-SSL-100h` chunk-32 encoder, decoder, joiner, and token files for ASR.
- Capture targets the built-in laptop microphone at approximately 1–3 metres in multi-speaker meetings.
- Recognition quality takes priority over latency; emit finalized transcript text rather than speculative partial text.
- Preserve valid received audio locally for replay; default retention is 24 hours.
- Never silently discard a valid received audio frame or recognizable fallback segment.
- DeepFilterNet processes 2.5-second chunks with 0.3-second overlap and starts with a 15 dB attenuation limit and disabled post-filter.
- Calibrate Silero VAD at thresholds 0.2, 0.35, and 0.5 using the far-field benchmark.
- Preserve user changes already present in `src/runtime/api.py`, `report_compilation/slide.md`, and `training-eval-suite`.
- Do not investigate or change why `Zipformer-SSL-100h` currently matches another checkpoint directory.

## File Structure

- `src/config/asr.py`: ASR model paths and accuracy-pipeline runtime settings.
- `src/types/audio.py`: Versioned WebSocket control messages and transcript quality metadata.
- `src/service/audio_capture.py`: Session WAV persistence, retention, and streaming resampling.
- `src/service/audio_preprocessor.py`: DeepFilterNet adapter, chunk overlap, and quality metrics.
- `src/service/diarization_engine.py`: Speaker profile aggregation and adapter around overlap/speaker components.
- `src/service/far_field_pipeline.py`: Per-connection orchestration from PCM through finalized utterances.
- `src/service/asr_engine.py`: Required Zipformer initialization and final segment decoding only.
- `src/runtime/api.py`: Thin WebSocket protocol adapter and lifecycle handling.
- `frontend/src/audio/pcm-capture.worklet.ts`: Native-rate PCM capture.
- `frontend/src/audio/meetingAudioClient.ts`: WebSocket protocol and capture lifecycle.
- `frontend/src/App.tsx`: UI integration and finalized transcript handling.
- `frontend/src/types.ts`: Session status and quality metadata types.
- `tests/unit/test_audio_capture.py`: Persistence and resampling tests.
- `tests/unit/test_audio_preprocessor.py`: Chunking, overlap, and metrics tests.
- `tests/unit/test_diarization_engine.py`: Stable profiles and fallback tests.
- `tests/unit/test_far_field_pipeline.py`: Boundary orchestration tests.
- `tests/unit/test_asr_engine.py`: Model path and final-decode tests.
- `tests/integration/test_api_streaming.py`: WebSocket protocol and recovery tests.
- `training-eval-suite/far_field_asr/`: Replay CLI, manifest schema, metrics, and reports.

---

### Task 1: Lock the Protocol, Configuration, and Required Model

**Files:**
- Create: `src/types/audio.py`
- Modify: `src/types/__init__.py`
- Modify: `src/config/asr.py`
- Modify: `tests/unit/test_asr_engine.py`
- Create: `tests/unit/test_audio_types.py`

**Interfaces:**
- Produces: `AudioSessionStart`, `AppliedAudioSettings`, `AudioQualityMetrics`, `FinalUtteranceEvent`, and expanded `AsrConfig`.
- Consumes: Pydantic base classes already used under `src/types` and `src/config`.

- [ ] **Step 1: Write failing config tests for the required model path and accuracy settings**

```python
def test_asr_config_uses_ssl_chunk_32_checkpoint() -> None:
    cfg = AsrConfig(_env_file=None)
    assert "Zipformer-SSL-100h" in cfg.encoder
    assert "chunk-32-left-128" in cfg.encoder
    assert "Zipformer-SSL-100h" in cfg.decoder
    assert "Zipformer-SSL-100h" in cfg.joiner
    assert cfg.emit_partials is False
    assert cfg.audio_retention_hours == 24
```

- [ ] **Step 2: Write failing protocol-model validation tests**

```python
def test_audio_session_start_requires_supported_protocol() -> None:
    start = AudioSessionStart(
        type="session_start", protocol_version=1,
        sample_rate=48000, channels=1,
        settings=AppliedAudioSettings(
            echo_cancellation=True,
            noise_suppression=True,
            auto_gain_control=True,
        ),
    )
    assert start.sample_rate == 48000

def test_audio_session_start_rejects_stereo() -> None:
    with pytest.raises(ValidationError):
        AudioSessionStart(
            type="session_start", protocol_version=1,
            sample_rate=48000, channels=2, settings={},
        )
```

- [ ] **Step 3: Run the targeted tests and verify red**

Run: `.venv/bin/pytest tests/unit/test_asr_engine.py tests/unit/test_audio_types.py -q`

Expected: FAIL because the protocol models and new configuration fields do not exist and paths still reference `Zipformer-30M-RNNT-Streaming-6000h`.

- [ ] **Step 4: Implement the protocol models and exact configuration defaults**

```python
class AppliedAudioSettings(BaseSchema):
    echo_cancellation: bool | None = None
    noise_suppression: bool | None = None
    auto_gain_control: bool | None = None

class AudioSessionStart(BaseSchema):
    type: Literal["session_start"]
    protocol_version: Literal[1]
    sample_rate: int = Field(ge=8000, le=192000)
    channels: Literal[1]
    settings: AppliedAudioSettings

class AudioQualityMetrics(BaseSchema):
    rms: float = Field(ge=0.0)
    peak: float = Field(ge=0.0)
    clipped: bool
    vad_confidence: float = Field(ge=0.0, le=1.0)
    speech_duration: float = Field(ge=0.0)

class FinalUtteranceEvent(BaseSchema):
    type: Literal["utterance"] = "utterance"
    id: int = Field(ge=1)
    session_id: str
    speaker: str
    text: str
    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(ge=0.0)
    source_sample_rate: int
    sample_rate: Literal[16000] = 16000
    quality: AudioQualityMetrics
    preprocessing_ms: float = Field(ge=0.0)
    diarization_ms: float = Field(ge=0.0)
    asr_ms: float = Field(ge=0.0)
    total_ms: float = Field(ge=0.0)
    degraded: bool = False
    fallback: bool = False
```

Add `emit_partials=False`, `audio_retention_hours=24`, `vad_threshold=0.35`, and the exact `Zipformer-SSL-100h` chunk-32 paths to `AsrConfig`.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/pytest tests/unit/test_asr_engine.py tests/unit/test_audio_types.py -q`

Expected: PASS.

```bash
git add src/config/asr.py src/types/audio.py src/types/__init__.py tests/unit/test_asr_engine.py tests/unit/test_audio_types.py
git commit -m "feat: define far-field audio protocol and model config"
```

### Task 2: Persist Native Audio and Resample Without Dropping Frames

**Files:**
- Create: `src/service/audio_capture.py`
- Create: `tests/unit/test_audio_capture.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `AudioSessionStart` from Task 1.
- Produces: `StreamingAudioSession.push(samples: np.ndarray) -> np.ndarray`, `flush() -> np.ndarray`, `close(retain: bool = False) -> Path`, and `cleanup_expired_recordings(root: Path, retention_hours: int) -> list[Path]`.

- [ ] **Step 1: Resolve and verify current python-soxr streaming documentation through Context7**

Run:

```bash
npx ctx7@latest library "python-soxr" "Python streaming resampling Float32 mono audio chunks with ResampleStream and final flush"
npx ctx7@latest docs <selected-library-id> "Python streaming resampling Float32 mono audio chunks with ResampleStream and final flush"
```

Expected: documentation confirms the current constructor and chunk/flush API. Use the documented API verbatim in the implementation.

- [ ] **Step 2: Write failing tests for frame preservation, rate conversion, WAV output, and cleanup**

```python
def test_streaming_session_preserves_duration_and_writes_source_wav(tmp_path: Path) -> None:
    source = np.sin(2 * np.pi * 440 * np.arange(48000) / 48000).astype(np.float32)
    session = StreamingAudioSession("s1", 48000, tmp_path)
    output = np.concatenate([session.push(x) for x in np.array_split(source, 17)])
    output = np.concatenate([output, session.flush()])
    wav_path = session.close(retain=True)
    assert abs(len(output) - 16000) <= 2
    samples, rate = sf.read(wav_path, dtype="float32")
    assert rate == 48000
    np.testing.assert_allclose(samples, source, atol=2e-4)

def test_cleanup_only_removes_expired_wav_files(tmp_path: Path) -> None:
    expired = make_recording(tmp_path, "expired.wav", age_hours=25)
    fresh = make_recording(tmp_path, "fresh.wav", age_hours=2)
    assert cleanup_expired_recordings(tmp_path, 24) == [expired]
    assert fresh.exists()
```

- [ ] **Step 3: Run tests and verify red**

Run: `.venv/bin/pytest tests/unit/test_audio_capture.py -q`

Expected: FAIL because `StreamingAudioSession` does not exist.

- [ ] **Step 4: Add `soxr` and `soundfile` dependencies and implement the session**

```python
class StreamingAudioSession:
    def __init__(self, session_id: str, source_rate: int, root: Path) -> None:
        self.session_id = session_id
        self.source_rate = source_rate
        self.path = root / f"{session_id}.wav"
        self._writer = sf.SoundFile(self.path, "w", samplerate=source_rate, channels=1, subtype="FLOAT")
        self._resampler = soxr.ResampleStream(source_rate, 16000, 1, dtype="float32", quality="HQ")

    def push(self, samples: np.ndarray) -> np.ndarray:
        samples = validate_mono_float32(samples)
        self._writer.write(samples)
        return np.asarray(self._resampler.resample_chunk(samples, last=False), dtype=np.float32)

    def flush(self) -> np.ndarray:
        return np.asarray(self._resampler.resample_chunk(np.empty(0, np.float32), last=True), dtype=np.float32)
```

Use `Path.mkdir(parents=True, exist_ok=True)`, UUID-derived filenames, explicit close semantics, and idempotent cleanup.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/pytest tests/unit/test_audio_capture.py -q`

Expected: PASS with duration error no greater than two samples.

```bash
git add pyproject.toml uv.lock src/service/audio_capture.py tests/unit/test_audio_capture.py
git commit -m "feat: persist and resample meeting audio"
```

### Task 3: Add an Injectable Accuracy-Mode Audio Preprocessor

**Files:**
- Create: `src/service/audio_preprocessor.py`
- Create: `tests/unit/test_audio_preprocessor.py`
- Create: `tests/manual/test_audio_preprocessor_smoke.py`
- Modify: `pyproject.toml`
- Modify: `src/config/asr.py`

**Interfaces:**
- Produces: `AudioPreprocessor.process(samples: np.ndarray) -> list[ProcessedAudioChunk]`, `flush() -> list[ProcessedAudioChunk]`, and `AudioPreprocessingUnavailable`.
- `ProcessedAudioChunk` fields: `samples`, `start_sample`, `end_sample`, `rms`, `peak`, `clipped`, `preprocessing_ms`.
- Consumes: resampled 16 kHz mono Float32 arrays from Task 2.

- [ ] **Step 1: Write failing deterministic overlap/chunking tests with a fake enhancer**

```python
def test_preprocessor_emits_2_5_second_chunks_with_0_3_second_context() -> None:
    enhancer = RecordingEnhancer()
    processor = AudioPreprocessor(enhancer, sample_rate=16000, chunk_seconds=2.5, overlap_seconds=0.3)
    emitted = processor.process(np.ones(16000 * 5, dtype=np.float32) * 0.01)
    assert len(emitted) == 2
    assert all(len(chunk.samples) == 40000 for chunk in emitted)
    assert enhancer.calls[1].shape[0] == 44800

def test_preprocessor_reports_quiet_signal_without_amplifying_it() -> None:
    processor = AudioPreprocessor(IdentityEnhancer(), 16000, 2.5, 0.3)
    [chunk] = processor.process(np.full(40000, 0.001, dtype=np.float32))
    assert chunk.rms == pytest.approx(0.001)
    assert chunk.clipped is False
```

- [ ] **Step 2: Run tests and verify red**

Run: `.venv/bin/pytest tests/unit/test_audio_preprocessor.py -q`

Expected: FAIL because the preprocessor module does not exist.

- [ ] **Step 3: Implement the narrow enhancer protocol and DeepFilterNet adapter**

```python
class Enhancer(Protocol):
    def enhance(self, samples: np.ndarray) -> np.ndarray: ...

class DeepFilterNetEnhancer:
    def __init__(self, atten_lim_db: float = 15.0, post_filter: bool = False) -> None:
        from df.enhance import enhance, init_df
        self._enhance = enhance
        self._model, self._state, _ = init_df(post_filter=post_filter)
        self._atten_lim_db = atten_lim_db

    def enhance(self, samples: np.ndarray) -> np.ndarray:
        source = torch.from_numpy(samples).float().unsqueeze(0)
        at_48k = torchaudio.functional.resample(source, 16000, self._state.sr())
        with torch.inference_mode():
            cleaned = self._enhance(self._model, self._state, at_48k, atten_lim_db=self._atten_lim_db)
        return torchaudio.functional.resample(cleaned, self._state.sr(), 16000).squeeze(0).cpu().numpy()
```

Raise `AudioPreprocessingUnavailable` at application startup when accuracy mode is enabled and `df` cannot import. Keep `IdentityEnhancer` injectable only for tests; production accuracy mode must not silently select it.

- [ ] **Step 4: Run unit tests, run an optional real-model smoke test, and commit**

Run: `.venv/bin/pytest tests/unit/test_audio_preprocessor.py -q`

Run after dependencies are installed: `.venv/bin/pytest -m real_model tests/manual/test_audio_preprocessor_smoke.py -q`

Expected: unit tests PASS; smoke test emits finite 16 kHz Float32 output with the expected duration.

```bash
git add pyproject.toml uv.lock src/config/asr.py src/service/audio_preprocessor.py tests/unit/test_audio_preprocessor.py tests/manual/test_audio_preprocessor_smoke.py
git commit -m "feat: add stateful far-field audio enhancement"
```

### Task 4: Stabilize Speaker Profiles and Provide Safe Diarization Fallback

**Files:**
- Create: `src/service/diarization_engine.py`
- Create: `src/service/diarization_models.py`
- Create: `tests/unit/test_diarization_engine.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: a VAD-complete enhanced segment plus a lightly processed segment on the same timeline.
- Produces: `DiarizedStream(speaker: str, samples: np.ndarray, fallback: bool)` and `DiarizationResult(streams: tuple[DiarizedStream, ...], has_overlap: bool, latency_ms: float)`.
- Wraps current OVD/TSE/BSS components behind `OverlapDetector`, `SpeakerEmbedder`, and `SourceSeparator` protocols.

- [ ] **Step 1: Write failing tests for aggregate profiles and fallback preservation**

```python
def test_same_speaker_updates_centroid_instead_of_creating_new_ids() -> None:
    engine = DiarizationEngine(
        overlap=NeverOverlap(), embedder=SequenceEmbedder([[1, 0], [.98, .02]]),
        separator=UnusedSeparator(), matching_threshold=.5,
    )
    first = engine.process(audio(), audio(), speech_duration=2.0, vad_confidence=.95)
    second = engine.process(audio(), audio(), speech_duration=2.0, vad_confidence=.95)
    assert first.streams[0].speaker == "Speaker 01"
    assert second.streams[0].speaker == "Speaker 01"
    assert engine.profile_count == 1

def test_overlap_failure_preserves_mixed_audio() -> None:
    source = audio()
    result = DiarizationEngine(AlwaysOverlap(), embedder(), FailingSeparator()).process(
        source, source, speech_duration=2.0, vad_confidence=.9,
    )
    assert result.streams[0].speaker == "Unknown Speaker"
    assert result.streams[0].fallback is True
    np.testing.assert_array_equal(result.streams[0].samples, source)
```

- [ ] **Step 2: Run tests and verify red**

Run: `.venv/bin/pytest tests/unit/test_diarization_engine.py -q`

Expected: FAIL because the new diarization boundary does not exist.

- [ ] **Step 3: Implement bounded profile aggregation and adapters**

```python
@dataclass
class SpeakerProfile:
    speaker: str
    centroid: np.ndarray
    observations: int

    def update(self, embedding: np.ndarray) -> None:
        weight = min(self.observations, 9)
        merged = (self.centroid * weight + embedding) / (weight + 1)
        self.centroid = merged / max(np.linalg.norm(merged), 1e-6)
        self.observations += 1
```

Only create/update profiles for `speech_duration >= 1.5` and `vad_confidence >= 0.9`. Catch overlap/TSE/BSS exceptions at this boundary, return the original mixed segment as `Unknown Speaker`, and expose the fallback flag.

In `diarization_models.py`, implement `PyannoteOverlapDetector`, `CamPlusPlusEmbedder`, `SpeakerBeamSeparator`, and `ConvTasNetSeparator` behind the protocols. Resolve their weights from `AIP491-G5-Audio-Preprocessing-and-Speaker-Diarization/prepare` through configuration without importing through the hyphenated directory name. Move only the narrow adapter logic required by `src`; do not commit duplicate model binaries. Validate every model path at startup and normalize every embedding before it reaches the profile pool.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/pytest tests/unit/test_diarization_engine.py -q`

Expected: PASS.

```bash
git add pyproject.toml uv.lock src/service/diarization_engine.py src/service/diarization_models.py tests/unit/test_diarization_engine.py
git commit -m "feat: add robust meeting speaker diarization"
```

### Task 5: Compose the Accuracy-First Per-Session Pipeline

**Files:**
- Create: `src/service/far_field_pipeline.py`
- Create: `tests/unit/test_far_field_pipeline.py`
- Modify: `src/service/asr_engine.py`
- Modify: `tests/unit/test_asr_engine.py`

**Interfaces:**
- Consumes: native PCM from Task 2, enhanced chunks from Task 3, diarized streams from Task 4, and `AsrEngine.decode_segment`.
- Produces: `FarFieldSession.push(samples: np.ndarray) -> tuple[FinalUtteranceEvent, ...]`, `flush() -> tuple[FinalUtteranceEvent, ...]`, and `close(retain: bool) -> Path`.

- [ ] **Step 1: Extend ASR tests to reject partial decoding and verify the required model constructor arguments**

```python
def test_engine_loads_ssl_chunk_32_transducer(monkeypatch, tmp_path) -> None:
    cfg = make_model_config(tmp_path, directory="Zipformer-SSL-100h")
    factory = Mock(return_value=FakeRecognizer())
    monkeypatch.setattr(sherpa_onnx.OnlineRecognizer, "from_transducer", factory)
    AsrEngine(cfg)
    assert "Zipformer-SSL-100h" in factory.call_args.kwargs["encoder"]
    assert "chunk-32-left-128" in factory.call_args.kwargs["encoder"]
```

- [ ] **Step 2: Write a failing pipeline test that processes each finalized stream exactly once**

```python
def test_completed_vad_segment_is_diarized_and_decoded_once(tmp_path: Path) -> None:
    asr = RecordingAsr("xin chào")
    session = build_session(tmp_path, vad=OneCompletedSegment(), diarizer=OneSpeaker(), asr=asr)
    events = session.push(native_audio())
    assert [event.text for event in events] == ["xin chào"]
    assert [event.speaker for event in events] == ["Speaker 01"]
    assert asr.decode_calls == 1
    assert events[0].quality.rms > 0

def test_flush_processes_remaining_vad_tail_once(tmp_path: Path) -> None:
    session = build_session(tmp_path, vad=TailOnFlush(), diarizer=OneSpeaker(), asr=RecordingAsr("kết thúc"))
    session.push(native_audio())
    assert [event.text for event in session.flush()] == ["kết thúc"]
```

- [ ] **Step 3: Run tests and verify red**

Run: `.venv/bin/pytest tests/unit/test_asr_engine.py tests/unit/test_far_field_pipeline.py -q`

Expected: FAIL because `FarFieldSession` does not exist and the current engine exposes continuous decoding.

- [ ] **Step 4: Implement composition with explicit timing and fallback metadata**

```python
class FarFieldSession:
    def push(self, samples: np.ndarray) -> tuple[FinalUtteranceEvent, ...]:
        resampled = self.audio.push(samples)
        events: list[FinalUtteranceEvent] = []
        for chunk in self.preprocessor.process(resampled):
            for speech in self.vad.accept(chunk.samples):
                diarized = self.diarizer.process(
                    speech.samples, speech.light_samples,
                    speech_duration=speech.duration,
                    vad_confidence=speech.confidence,
                )
                for stream in diarized.streams:
                    text, asr_ms = self._decode_timed(stream.samples)
                    if text:
                        events.append(self._event(speech, stream, text, chunk, diarized, asr_ms))
        return tuple(events)
```

Keep ASR finalization with 0.4-second Float32 zero padding and `input_finished()`. Remove production calls to `decode_stream_step`; no partial event is emitted.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/pytest tests/unit/test_asr_engine.py tests/unit/test_far_field_pipeline.py -q`

Expected: PASS, including exactly one ASR decode per output stream.

```bash
git add src/service/asr_engine.py src/service/far_field_pipeline.py tests/unit/test_asr_engine.py tests/unit/test_far_field_pipeline.py
git commit -m "feat: compose accuracy-first meeting audio pipeline"
```

### Task 6: Replace the WebSocket Handler With the Versioned Session Protocol

**Files:**
- Modify: `src/runtime/api.py`
- Modify: `tests/integration/test_api_streaming.py`

**Interfaces:**
- Consumes: `AudioSessionStart` and `FarFieldSession`.
- Produces: `session_ready`, `processing_status`, finalized `utterance`, `session_closed`, and structured `pipeline_error` JSON events.

- [ ] **Step 1: Write failing WebSocket tests with an injected fake session factory**

```python
def test_websocket_requires_session_start_before_pcm() -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_bytes(np.zeros(128, np.float32).tobytes())
        message = ws.receive_json()
        assert message["type"] == "pipeline_error"
        assert message["stage"] == "protocol"

def test_websocket_acknowledges_applied_config_and_emits_only_final_text() -> None:
    app = build_test_app(audio_session_factory=FakeSessionFactory())
    with TestClient(app).websocket_connect("/ws") as ws:
        ws.send_json(valid_session_start())
        assert ws.receive_json()["type"] == "session_ready"
        ws.send_bytes(np.ones(4096, np.float32).tobytes())
        event = ws.receive_json()
        assert event["type"] == "utterance"
        assert event["text"] == "xin chào"
        assert event["quality"]["rms"] > 0
```

- [ ] **Step 2: Run tests and verify red**

Run: `.venv/bin/pytest tests/integration/test_api_streaming.py -q`

Expected: FAIL because the current endpoint accepts PCM immediately and emits partial events.

- [ ] **Step 3: Refactor `create_app` to accept an audio-session factory and keep the handler thin**

```python
def create_app(
    orchestrator: StreamingOrchestrator | None = None,
    audio_session_factory: AudioSessionFactory | None = None,
) -> FastAPI:
    ...

@app.websocket("/ws")
async def websocket_asr_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    start = await receive_session_start(websocket)
    session = app.state.audio_session_factory.create(start)
    await websocket.send_json(session.ready_event())
    try:
        await consume_audio(websocket, session)
    finally:
        await send_events(websocket, session.flush())
        session.close()
```

Preserve the user's existing `_ensure_ld_library_path()` change. Validate binary frames with `_decode_pcm_float32`, report queue/processing state, persist all accepted frames, and never log transcript bodies by default.

- [ ] **Step 4: Run integration and existing runtime tests, then commit**

Run: `.venv/bin/pytest tests/integration/test_api_streaming.py tests/unit/test_runtime_layer_rules.py -q`

Expected: PASS.

```bash
git add src/runtime/api.py tests/integration/test_api_streaming.py
git commit -m "feat: stream finalized far-field transcripts"
```

### Task 7: Move Browser Capture to AudioWorklet and Report Applied Settings

**Files:**
- Create: `frontend/src/audio/pcm-capture.worklet.ts`
- Create: `frontend/src/audio/meetingAudioClient.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/vite.config.ts`

**Interfaces:**
- Produces: `MeetingAudioClient.start(deviceId: string)`, `pause()`, `resume()`, `stop()`, and typed event callbacks.
- Consumes: WebSocket protocol from Task 6.

- [ ] **Step 1: Extract a typed client and add compile-time protocol fixtures**

```typescript
export type AudioSessionStart = {
  type: 'session_start';
  protocol_version: 1;
  sample_rate: number;
  channels: 1;
  settings: {
    echo_cancellation: boolean | null;
    noise_suppression: boolean | null;
    auto_gain_control: boolean | null;
  };
};

export type ProcessingState = 'idle' | 'recording' | 'queued' | 'finalizing' | 'degraded' | 'failed';
```

- [ ] **Step 2: Implement the worklet without frontend resampling**

```typescript
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs: Float32Array[][]): boolean {
    const mono = inputs[0]?.[0];
    if (mono?.length) this.port.postMessage(mono.slice(), [mono.slice().buffer]);
    return true;
  }
}
registerProcessor('pcm-capture', PcmCaptureProcessor);
```

In the final implementation, allocate one copied `Float32Array`, transfer that same buffer once, and do not call the old `downsampleBuffer`.

- [ ] **Step 3: Implement capture negotiation and applied-setting reporting**

```typescript
const stream = await navigator.mediaDevices.getUserMedia({
  audio: {
    deviceId: deviceId ? { exact: deviceId } : undefined,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    channelCount: 1,
  },
});
const trackSettings = stream.getAudioTracks()[0].getSettings();
sendSessionStart({
  sample_rate: audioContext.sampleRate,
  channels: 1,
  settings: {
    echo_cancellation: trackSettings.echoCancellation ?? null,
    noise_suppression: trackSettings.noiseSuppression ?? null,
    auto_gain_control: trackSettings.autoGainControl ?? null,
  },
});
```

Wait for `session_ready` before forwarding binary PCM. Buffer worklet frames until acknowledgement, with a strict byte limit that fails visibly rather than silently dropping data.

- [ ] **Step 4: Replace the audio/WebSocket block in `App.tsx` and remove misleading controls**

Remove `ScriptProcessorNode`, `downsampleBuffer`, partial transcript handling, and local-only VAD/provider/thread controls. Add processing-state UI and map finalized quality metadata into `TranscriptSegment`.

- [ ] **Step 5: Build, lint, and commit**

Run: `pnpm --dir frontend build`

Run: `pnpm --dir frontend lint`

Expected: both commands exit 0; the bundle includes the worklet and no `createScriptProcessor` or `downsampleBuffer` reference remains.

```bash
git add frontend/src/audio/pcm-capture.worklet.ts frontend/src/audio/meetingAudioClient.ts frontend/src/App.tsx frontend/src/types.ts frontend/vite.config.ts
git commit -m "feat: capture native microphone audio with AudioWorklet"
```

### Task 8: Add Far-Field Replay Evaluation to the Project Evaluation Suite

**Files:**
- Create: `training-eval-suite/far_field_asr/README.md`
- Create: `training-eval-suite/far_field_asr/manifest.schema.json`
- Create: `training-eval-suite/far_field_asr/replay.py`
- Create: `training-eval-suite/far_field_asr/metrics.py`
- Create: `training-eval-suite/far_field_asr/tests/test_metrics.py`

**Interfaces:**
- Consumes: recorded WAV files, reference transcript/speaker annotations, and the replayable backend pipeline.
- Produces: JSON and Markdown reports containing WER, CER, VAD miss rate, speaker error/consistency, clipping, real-time factor, and finalization latency.

- [ ] **Step 1: Write failing metric tests with exact expected values**

```python
def test_error_rates_and_vad_miss_rate() -> None:
    report = score_case(
        reference_words=["xin", "chào", "mọi", "người"],
        hypothesis_words=["xin", "chào", "người"],
        expected_utterances=2,
        detected_utterances=1,
    )
    assert report.wer == pytest.approx(0.25)
    assert report.vad_miss_rate == pytest.approx(0.5)
```

- [ ] **Step 2: Implement manifest validation and deterministic metrics**

The manifest requires `id`, `wav`, `reference_text`, `distance_m`, `noise_condition`, `speakers`, and optional overlap intervals. Reject missing WAV files and sample rates not supported by the replay entry point.

- [ ] **Step 3: Implement baseline/new-pipeline replay**

```bash
python -m far_field_asr.replay \
  --manifest far_field_asr/data/manifest.json \
  --baseline current \
  --candidate accuracy \
  --output far_field_asr/reports/latest.json
```

The replay must feed identical decoded WAV samples into both pipelines and include full configuration/model hashes in the report.

- [ ] **Step 4: Run tests and commit inside `training-eval-suite`**

Run: `pytest training-eval-suite/far_field_asr/tests/test_metrics.py -q`

Expected: PASS.

Commit inside the evaluation repository so the parent project records only its existing nested-repository state:

```bash
git -C training-eval-suite add far_field_asr
git -C training-eval-suite commit -m "feat: evaluate far-field meeting ASR"
```

### Task 9: End-to-End Verification and Acceptance Report

**Files:**
- Create: `tests/e2e/test_far_field_audio_replay.py`
- Modify: `frontend/README.md`
- Modify: `src/runtime/README.md`
- Create: `docs/generated/far-field-asr-acceptance.md`

**Interfaces:**
- Consumes: all previous tasks and recorded benchmark fixtures.
- Produces: a reproducible verification command and evidence against every acceptance criterion.

- [ ] **Step 1: Add an end-to-end synthetic replay test**

```python
def test_recorded_pcm_survives_disconnect_and_replay(tmp_path: Path) -> None:
    app, factory = build_accuracy_app(tmp_path)
    send_session_start_and_pcm_then_disconnect(app, fixture_pcm())
    wav = factory.last_session.recording_path
    assert wav.exists()
    events = replay_recording(wav, factory.pipeline)
    assert all(event.type == "utterance" for event in events)
    assert factory.last_session.accepted_samples == len(fixture_pcm())
```

- [ ] **Step 2: Run the focused backend, frontend, and layer checks**

Run:

```bash
.venv/bin/pytest tests/unit/test_audio_types.py tests/unit/test_audio_capture.py tests/unit/test_audio_preprocessor.py tests/unit/test_diarization_engine.py tests/unit/test_asr_engine.py tests/unit/test_far_field_pipeline.py tests/integration/test_api_streaming.py tests/e2e/test_far_field_audio_replay.py -q
pnpm --dir frontend build
pnpm --dir frontend lint
```

Expected: all commands exit 0.

- [ ] **Step 3: Run the complete non-real-model regression suite**

Run: `.venv/bin/pytest -q`

Expected: all non-`real_model` tests PASS.

- [ ] **Step 4: Run real-model readiness and one captured-room benchmark**

Run the backend health check with CUDA enabled, then run the far-field replay command from Task 8. Record actual WER/CER, VAD misses, speaker consistency, and latency in `docs/generated/far-field-asr-acceptance.md`. Do not claim the numeric acceptance targets until this report contains measured results.

- [ ] **Step 5: Scan for removed legacy paths and debug instrumentation**

Run:

```bash
rg -n 'createScriptProcessor|downsampleBuffer|partial_utterance|\[DEBUG-' frontend/src src tests
```

Expected: no production references to legacy capture, partial ASR, or temporary tagged instrumentation.

- [ ] **Step 6: Commit documentation and end-to-end coverage**

```bash
git add tests/e2e/test_far_field_audio_replay.py frontend/README.md src/runtime/README.md docs/generated/far-field-asr-acceptance.md
git commit -m "test: verify far-field meeting ASR pipeline"
```
