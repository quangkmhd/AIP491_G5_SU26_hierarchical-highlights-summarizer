# Custom_10h Real-Time Demo Recording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and record a reproducible web demo that plays `Custom_10h` WAV files sequentially for one hour at real-time speed, streams the same PCM through the current ASR/recap pipeline, and exports a synchronized 1920×1080 MP4 with audible audio.

**Architecture:** A deep `Custom10hTimeline` module hides corpus validation, strict manifest-order scheduling, allowlisted audio lookup, and deterministic WAV rendering behind one small interface. Demo-only FastAPI routes expose that prepared timeline, a browser `DemoAudioClient` plays and submits one WAV at a time through the existing `/ws`, and a Python recorder drives Chromium with Playwright before muxing the deterministic audio and recorded WebM with FFmpeg.

**Tech Stack:** Python 3.12, FastAPI, Pydantic Settings, React 19, TypeScript 6, Web Audio API, WebSocket, Playwright for Python, FFmpeg/FFprobe, pytest.

## Global Constraints

- Work on the current `main` branch; do not create a worktree.
- Preserve the user's modified `report_compilation/slide.md`, dirty nested `training-eval-suite`, and untracked `AIP491-G5-Audio-Preprocessing-and-Speaker-Diarization/`.
- Read WAV rows strictly in physical `recordings.jsonl` order; never sort, randomize, overlap, or parallelize playback.
- Finish each WAV completely, then emit exactly 10,400 zero samples (0.65 seconds at 16 kHz) before the next WAV.
- The source timeline is exactly 57,600,000 mono samples at 16 kHz; do not truncate speech to reach it.
- Submit audio at 1.0x wall-clock speed through the current `/ws`; do not inject `supervisions.jsonl` text into ASR or recap events.
- Keep demo routes disabled unless `DEMO_ENABLED=true` or an explicit test timeline is injected.
- Keep normal microphone recording behaviour unchanged when demo mode is absent.
- Record 1920×1080 WebM with Playwright, close the browser context before consuming the artifact, then mux H.264/AAC MP4 with FFmpeg.
- Allow at most 90 seconds after the source timeline for `meeting-completed` and `session_closed`.
- All production behaviour changes use red-green-refactor; generated demo artifacts stay under ignored `outputs/demo/`.

---

### Task 1: Deterministic Custom_10h Timeline Module

**Files:**
- Create: `src/service/demo_timeline.py`
- Create: `tests/unit/test_demo_timeline.py`
- Modify: `src/service/__init__.py`

**Interfaces:**
- Consumes: `data_dir/recordings.jsonl`, mono 16 kHz WAV files, `duration_seconds`, and `gap_seconds`.
- Produces: `Custom10hTimeline.build(data_dir, duration_seconds, gap_seconds)`, `manifest_payload()`, `resolve_audio(recording_id)`, and `write_wav(output, pauses=())`.

- [ ] **Step 1: Write failing tests for physical order and exact sequential boundaries**

```python
def test_build_preserves_jsonl_order_and_never_overlaps(tmp_path: Path) -> None:
    data_dir = make_custom10h_fixture(
        tmp_path,
        [("z-first_00001", 1600), ("a-second_00002", 3200), ("m-third_00003", 1600)],
    )

    timeline = Custom10hTimeline.build(
        data_dir=data_dir,
        duration_seconds=1.0,
        gap_seconds=0.1,
    )

    assert [item.recording_id for item in timeline.items] == [
        "z-first_00001",
        "a-second_00002",
        "m-third_00003",
    ]
    assert [(item.start_sample, item.end_sample) for item in timeline.items] == [
        (0, 1600),
        (3200, 6400),
        (8000, 9600),
    ]
    assert timeline.total_samples == 16_000
    assert timeline.padding_samples == 4_800
```

Add this parameterized validation surface and a separate final-WAV assertion:

```python
@pytest.mark.parametrize(
    ("fixture_kind", "message"),
    [
        ("duplicate-id", "duplicate recording id"),
        ("stereo", "must be mono"),
        ("wrong-rate", "expected 16000"),
        ("escaping-path", "outside Custom_10h"),
    ],
)
def test_build_rejects_invalid_corpus_rows(tmp_path, fixture_kind, message) -> None:
    data_dir = make_invalid_fixture(tmp_path, fixture_kind)
    with pytest.raises(ValueError, match=message):
        Custom10hTimeline.build(data_dir, duration_seconds=1.0, gap_seconds=0.1)

def test_build_skips_instead_of_truncating_the_first_wav_that_cannot_fit(tmp_path) -> None:
    data_dir = make_custom10h_fixture(
        tmp_path,
        [("fits_00001", 8_000), ("too-long_00002", 12_000)],
    )
    timeline = Custom10hTimeline.build(data_dir, duration_seconds=1.0, gap_seconds=0.1)
    assert [item.recording_id for item in timeline.items] == ["fits_00001"]
    assert timeline.items[0].sample_count == 8_000
    assert timeline.total_samples == 16_000

def test_resolve_and_write_are_limited_to_the_prepared_timeline(tmp_path) -> None:
    data_dir = make_custom10h_fixture(tmp_path, [("only_00001", 8_000)])
    timeline = Custom10hTimeline.build(data_dir, duration_seconds=1.0, gap_seconds=0.1)
    assert timeline.resolve_audio("only_00001").is_file()
    with pytest.raises(KeyError, match="unknown recording id"):
        timeline.resolve_audio("missing_00002")

    output = timeline.write_wav(tmp_path / "timeline.wav")
    with wave.open(str(output), "rb") as stream:
        assert stream.getnchannels() == 1
        assert stream.getframerate() == 16_000
        assert stream.getnframes() == 16_000
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH="$PWD" .venv/bin/pytest tests/unit/test_demo_timeline.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'src.service.demo_timeline'`.

- [ ] **Step 3: Implement the timeline data model and builder**

```python
SAMPLE_RATE = 16_000

@dataclass(frozen=True, slots=True)
class DemoTimelineItem:
    line_number: int
    recording_id: str
    relative_path: str
    wav_path: Path
    sample_count: int
    start_sample: int
    end_sample: int
    gap_samples: int
    sha256: str

@dataclass(frozen=True, slots=True)
class PlaybackPause:
    after_sample: int
    duration_samples: int

@dataclass(frozen=True, slots=True)
class Custom10hTimeline:
    data_dir: Path
    total_samples: int
    gap_samples: int
    padding_samples: int
    recordings_manifest_sha256: str
    items: tuple[DemoTimelineItem, ...]
```

Expose the exact method signatures stated in **Interfaces**. In `build`, compute `target_samples = round(duration_seconds * SAMPLE_RATE)` and `gap_samples = round(gap_seconds * SAMPLE_RATE)`, then iterate the JSONL stream directly with `enumerate(stream, start=1)`. Resolve each relative path under `data_dir`, validate WAV metadata with `wave`, compute boundaries in integer samples, stop at the first complete WAV that cannot fit, and set `padding_samples = target_samples - cursor` after the last scheduled gap. Never inspect `supervisions.jsonl`.

- [ ] **Step 4: Implement deterministic manifest and WAV evidence**

`manifest_payload()` must omit absolute paths and include `schema_version`, `sample_rate`, `duration_samples`, `gap_samples`, `padding_samples`, `recordings_manifest_sha256`, and every scheduled entry. `write_wav()` streams source frames instead of holding one hour in RAM; optional pauses insert zero samples at `after_sample` positions.

- [ ] **Step 5: Run focused and layer tests and verify GREEN**

Run:

```bash
PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/unit/test_demo_timeline.py \
  tests/unit/test_service_layer_rules.py -q
```

Expected: all tests pass and `git diff --check` is clean.

- [ ] **Step 6: Commit the timeline module**

```bash
git add src/service/demo_timeline.py src/service/__init__.py tests/unit/test_demo_timeline.py
git commit -m "feat: build sequential Custom_10h demo timelines"
```

---

### Task 2: Demo Configuration and Allowlisted FastAPI Routes

**Files:**
- Create: `src/config/demo.py`
- Modify: `src/config/__init__.py`
- Modify: `src/runtime/api.py:78-168`
- Modify: `tests/integration/test_api_streaming.py`
- Modify: `tests/unit/test_layer_rule_config.py`

**Interfaces:**
- Consumes: `Custom10hTimeline`, `DEMO_ENABLED`, `DEMO_DATA_DIR`, `DEMO_DURATION_SECONDS`, and `DEMO_GAP_SECONDS`.
- Produces: disabled-by-default `/api/v1/demo/custom10h/status`, `/manifest`, and `/audio/{recording_id}` routes.

- [ ] **Step 1: Write failing configuration and disabled-route tests**

```python
def test_demo_config_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("DEMO_ENABLED", raising=False)
    assert DemoConfig(_env_file=None).enabled is False

def test_demo_routes_are_not_registered_without_demo_timeline() -> None:
    app = build_test_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/demo/custom10h/status").status_code == 404
```

- [ ] **Step 2: Write failing enabled-route and allowlist tests**

```python
def test_demo_audio_route_serves_only_manifest_ids(tmp_path: Path) -> None:
    timeline = build_two_wav_timeline(tmp_path)
    app = build_test_app(demo_timeline=timeline)
    with TestClient(app) as client:
        manifest = client.get("/api/v1/demo/custom10h/manifest")
        assert manifest.status_code == 200
        assert [row["recording_id"] for row in manifest.json()["items"]] == ["b_00001", "a_00002"]
        assert client.get("/api/v1/demo/custom10h/audio/b_00001").status_code == 200
        assert client.get("/api/v1/demo/custom10h/audio/../../.env").status_code in {404, 422}
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/integration/test_api_streaming.py \
  tests/unit/test_layer_rule_config.py -q
```

Expected: imports or assertions fail because `DemoConfig` and demo route injection do not exist.

- [ ] **Step 4: Implement `DemoConfig`**

```python
class DemoConfig(ConfigBase):
    model_config = ConfigBase.model_config | {"env_prefix": "DEMO_"}

    enabled: bool = False
    data_dir: str = str(
        _PROJECT_ROOT / "training-eval-suite" / "data" / "Custom_10h"
    )
    duration_seconds: float = Field(default=3600.0, gt=0.0, le=3600.0)
    gap_seconds: float = Field(default=0.65, ge=0.5, le=2.0)
```

- [ ] **Step 5: Add the explicit demo seam to `create_app`**

Change the interface to:

```python
def create_app(
    orchestrator: StreamingOrchestrator | None = None,
    audio_session_factory: object | None = None,
    demo_timeline: Custom10hTimeline | None = None,
) -> FastAPI:
```

When `demo_timeline` is injected, register demo routes directly. Otherwise construct it only when `DemoConfig().enabled` is true. Store it in `app.state.demo_timeline`. Return `FileResponse` only for `timeline.resolve_audio(recording_id)` and set `media_type="audio/wav"`.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/integration/test_api_streaming.py \
  tests/unit/test_layer_rule_config.py \
  tests/unit/test_runtime_layer_rules.py -q
```

Expected: all tests pass; existing `/ws` protocol tests remain unchanged.

- [ ] **Step 7: Commit config and routes**

```bash
git add src/config/demo.py src/config/__init__.py src/runtime/api.py \
  tests/integration/test_api_streaming.py tests/unit/test_layer_rule_config.py
git commit -m "feat: expose gated Custom_10h demo audio"
```

---

### Task 3: Browser Audio Session Transport and Sequential Demo Client

**Files:**
- Create: `frontend/src/audio/audioSessionSocket.ts`
- Create: `frontend/src/audio/demoAudioClient.ts`
- Modify: `frontend/src/audio/meetingAudioClient.ts:1-289`
- Modify: `frontend/src/types.ts`
- Modify: `tests/ui/test_prototype_streaming.py`

**Interfaces:**
- Consumes: the demo manifest/audio routes, one `AudioContext({sampleRate: 16000})`, and existing `/ws` event callbacks.
- Produces: `AudioSessionSocket` shared by microphone/demo sources and `DemoAudioClient.start/pause/resume/stop`.

- [ ] **Step 1: Add a failing browser test for strict fetch and playback order**

Extend the Playwright background server with an injected three-WAV timeline whose IDs are deliberately non-sortable (`z-first`, `a-second`, `m-third`). Record HTTP requests and expose demo trace state from the page.

```python
def test_demo_plays_manifest_audio_sequentially_without_microphone(self) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{self.base_url}/?demo=custom10h")
        page.get_by_role("button", name="Bắt đầu demo").click()
        page.wait_for_function("document.body.dataset.demoState === 'completed'")
        trace = page.evaluate("window.__vietAsrDemoTrace")

    assert trace["completedRecordingIds"] == ["z-first", "a-second", "m-third"]
    assert trace["maxConcurrentAudio"] == 1
    assert trace["microphoneRequested"] is False
```

- [ ] **Step 2: Run the new browser test and verify RED**

Run:

```bash
pnpm --dir frontend build
RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/ui/test_prototype_streaming.py::PrototypeStructureTests::test_demo_plays_manifest_audio_sequentially_without_microphone -q
```

Expected: fail because the `Bắt đầu demo` control and demo client do not exist.

- [ ] **Step 3: Extract the shared WebSocket transport**

Implement this narrow interface:

```ts
export interface AudioSessionStartPayload {
  sample_rate: number;
  channels: 1;
  settings: {
    echo_cancellation: boolean | null;
    noise_suppression: boolean | null;
    auto_gain_control: boolean | null;
  };
}

export class AudioSessionSocket {
  constructor(options: MeetingSocketOptions);
  open(start: AudioSessionStartPayload): Promise<void>;
  send(frame: Float32Array): void;
  finish(retain?: boolean): Promise<void>;
  close(): void;
  get bufferedAmount(): number;
}
```

Move the existing connection timeout, session-ready handling, server-event parsing, pending-byte limit, pipeline errors, finalization timeout, and `session_closed` wait into this module. Change `MeetingAudioClient` to delegate only those responsibilities while retaining microphone/Web AudioWorklet ownership.

- [ ] **Step 4: Define demo manifest and trace types**

```ts
export interface DemoTimelineItem {
  line_number: number;
  recording_id: string;
  relative_path: string;
  sample_count: number;
  start_sample: number;
  end_sample: number;
  gap_samples: number;
  sha256: string;
}

export interface DemoTimelineManifest {
  sample_rate: 16000;
  duration_samples: number;
  gap_samples: number;
  padding_samples: number;
  items: DemoTimelineItem[];
}
```

- [ ] **Step 5: Implement `DemoAudioClient` with one active WAV**

```ts
export class DemoAudioClient {
  async start(): Promise<void>;
  pause(): Promise<void>;
  resume(): Promise<void>;
  stop(retain?: boolean): Promise<void>;

  private async playItem(item: DemoTimelineItem): Promise<void>;
  private async emitFrames(samples: Float32Array): Promise<void>;
  private async emitSilence(sampleCount: number): Promise<void>;
  private async waitForWritable(): Promise<void>;
}
```

Use 1,600-sample frames. Fetch exactly `items[index]`, validate decoded mono sample rate/count, start one `AudioBufferSourceNode`, submit frames against `audioContext.currentTime`, await `source.onended`, then emit the configured silent gap before incrementing the index. Prefetch only `items[index + 1]`. Update `window.__vietAsrDemoTrace` and `document.body.dataset.demoState` at stable state transitions.

- [ ] **Step 6: Implement shared pause/backpressure timing**

When `bufferedAmount` crosses the soft threshold, suspend the `AudioContext`, stop advancing the sample cursor, append `{type:"pause", after_sample, started_epoch_ms}` to the trace, and resume only after draining. Abort with `failed` when the hard timeout expires. `pause()` and `resume()` use the same mechanism.

- [ ] **Step 7: Verify demo client and microphone regressions GREEN**

Run:

```bash
pnpm --dir frontend build
pnpm --dir frontend lint
RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/ui/test_prototype_streaming.py \
  tests/integration/test_api_streaming.py -q
```

Expected: strict-order demo test and all existing browser/microphone tests pass.

- [ ] **Step 8: Commit transport and demo client**

```bash
git add frontend/src/audio/audioSessionSocket.ts \
  frontend/src/audio/demoAudioClient.ts \
  frontend/src/audio/meetingAudioClient.ts \
  frontend/src/types.ts tests/ui/test_prototype_streaming.py
git commit -m "feat: stream sequential demo audio through the browser"
```

---

### Task 4: Demo UI and Normal Recap Rendering

**Files:**
- Create: `frontend/src/components/DemoStatus.tsx`
- Modify: `frontend/src/App.tsx:1-316`
- Modify: `frontend/src/components/TranscriptPanel.tsx:1-300`
- Modify: `frontend/src/components/FloatingControls.tsx`
- Modify: `tests/ui/test_prototype_streaming.py`

**Interfaces:**
- Consumes: `DemoAudioClient` callbacks and the existing `handleServerEvent` recap path.
- Produces: query-driven demo controls, live badge/progress, and stable automation markers without changing the standard mic UI.

- [ ] **Step 1: Add failing UI tests for the demo badge, progress, and recap**

```python
def test_demo_ui_renders_real_utterance_and_final_recap(self) -> None:
    page.goto(f"{self.base_url}/?demo=custom10h")
    page.get_by_role("button", name="Bắt đầu demo").click()
    page.wait_for_selector("[data-testid='transcript-utterance']")
    page.wait_for_function("document.body.dataset.demoState === 'completed'")
    assert page.get_by_text("LIVE DEMO · Custom_10h").is_visible()
    assert page.get_by_text("Meeting Recap").is_visible()
    assert page.locator("[data-testid='demo-progress']").get_attribute("aria-valuenow") == "100"
```

Add a standard-route regression test:

```python
def test_standard_ui_does_not_enter_demo_mode(self) -> None:
    page.goto(f"{self.base_url}/")
    assert page.get_by_text("LIVE DEMO · Custom_10h").count() == 0
    assert page.get_by_role("button", name="Bắt đầu demo").count() == 0
    assert page.locator("select[title='Select Microphone Input']").count() <= 1
```

- [ ] **Step 2: Run the focused UI tests and verify RED**

```bash
pnpm --dir frontend build
RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/ui/test_prototype_streaming.py::PrototypeStructureTests::test_demo_ui_renders_real_utterance_and_final_recap -q
```

Expected: fail because the demo badge, progress, and start button do not exist.

- [ ] **Step 3: Add query-driven lifecycle to `App`**

Compute `const demoMode = new URLSearchParams(window.location.search).get('demo') === 'custom10h'`. Reuse one `createSession(title)` helper for mic and demo sessions. Construct `DemoAudioClient` only from `handleStartDemo`, pass `handleServerEvent` unchanged, and title the session `Custom_10h · Real-time 1-hour Demo`.

- [ ] **Step 4: Render focused demo status**

```tsx
<DemoStatus
  visible={demoMode}
  state={demoState}
  recordingId={demoProgress.recordingId}
  elapsedSamples={demoProgress.elapsedSamples}
  totalSamples={demoProgress.totalSamples}
/>
```

`DemoStatus` owns only badge/progress formatting. `TranscriptPanel` continues to render utterances and recap data through its existing props. Add `data-testid="transcript-utterance"` to the existing utterance card, not a duplicate demo transcript view.

- [ ] **Step 5: Keep finalization visible for the recorder**

Set `document.body.dataset.demoState` to `finalizing` after the 3,600-second cursor completes, then `completed` only after both `meeting-completed` and `session_closed` have passed through `handleServerEvent`. Surface errors as `failed` with an actionable message in the demo status area.

- [ ] **Step 6: Run frontend, UI, and integration verification GREEN**

```bash
pnpm --dir frontend build
pnpm --dir frontend lint
RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/ui/test_prototype_streaming.py \
  tests/integration/test_api_streaming.py -q
```

- [ ] **Step 7: Commit the demo UI**

```bash
git add frontend/src/App.tsx frontend/src/components/DemoStatus.tsx \
  frontend/src/components/TranscriptPanel.tsx \
  frontend/src/components/FloatingControls.tsx \
  tests/ui/test_prototype_streaming.py
git commit -m "feat: present the real-time Custom_10h demo"
```

---

### Task 5: Playwright Recorder, FFmpeg Muxer, and Evidence Report

**Files:**
- Create: `src/runtime/demo_recorder.py`
- Create: `scripts/record_custom10h_demo.py`
- Create: `tests/unit/test_demo_recorder.py`
- Modify: `src/runtime/README.md`

**Interfaces:**
- Consumes: output path, duration, current project environment, `Custom10hTimeline`, Playwright, FFmpeg, and the page demo trace.
- Produces: `record_demo(config: RecorderConfig) -> DemoRunResult`, WebM/WAV/MP4/log/FFprobe artifacts, and a non-zero exit on incomplete runs.

- [ ] **Step 1: Write failing tests for FFmpeg command and completion gates**

```python
def test_ffmpeg_command_muxes_delayed_audio_and_keeps_video_postroll(tmp_path: Path) -> None:
    cmd = build_ffmpeg_command(
        webm=tmp_path / "raw.webm",
        wav=tmp_path / "timeline.wav",
        audio_delay_ms=2300,
        output=tmp_path / "demo.mp4",
    )
    assert cmd[:2] == ["ffmpeg", "-y"]
    assert "adelay=2300:all=1,apad" in cmd
    assert ["-c:v", "libx264"] == cmd[cmd.index("-c:v"):cmd.index("-c:v") + 2]
    assert ["-c:a", "aac"] == cmd[cmd.index("-c:a"):cmd.index("-c:a") + 2]

def test_run_cannot_succeed_without_both_completion_events() -> None:
    with pytest.raises(DemoRecordingError, match="meeting-completed"):
        validate_completion({"session_closed": True, "meeting_completed": False})
```

Add these explicit cases:

```python
def test_validate_free_space_requires_eight_gib(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        shutil,
        "disk_usage",
        lambda _: SimpleNamespace(free=7 * 1024**3),
    )
    with pytest.raises(DemoRecordingError, match="8 GiB"):
        validate_free_space(tmp_path)

@pytest.mark.parametrize(
    "streams",
    [[], [{"codec_type": "video"}], [{"codec_type": "audio"}]],
)
def test_validate_probe_requires_audio_and_video(streams) -> None:
    with pytest.raises(DemoRecordingError, match="audio and video"):
        validate_ffprobe({"streams": streams})

def test_trace_pauses_are_converted_to_sample_offsets() -> None:
    pauses = playback_pauses_from_trace(
        [{"after_sample": 3200, "duration_ms": 250}],
        sample_rate=16_000,
    )
    assert pauses == [PlaybackPause(after_sample=3200, duration_samples=4000)]

def test_failed_run_keeps_existing_evidence(tmp_path: Path) -> None:
    partial = tmp_path / "raw.webm"
    partial.write_bytes(b"partial-video")
    preserve_partial_artifacts(tmp_path)
    assert partial.read_bytes() == b"partial-video"
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
PYTHONPATH="$PWD" .venv/bin/pytest tests/unit/test_demo_recorder.py -q
```

Expected: import failure because `src.runtime.demo_recorder` does not exist.

- [ ] **Step 3: Implement recorder contracts and preflight**

```python
@dataclass(frozen=True, slots=True)
class RecorderConfig:
    data_dir: Path
    duration_seconds: float
    output: Path
    width: int = 1920
    height: int = 1080
    finalization_timeout_seconds: float = 90.0

@dataclass(frozen=True, slots=True)
class DemoRunResult:
    run_dir: Path
    mp4: Path
    webm: Path
    wav: Path
    ffprobe: Path
    manifest: Path
```

Expose `record_demo(config: RecorderConfig) -> DemoRunResult`. It returns only after MP4 and FFprobe validation and raises `DemoRecordingError` on every failed completion gate. Preflight resolves `pnpm`, Chromium, `ffmpeg`, and `ffprobe`; checks dataset/model files and at least 8 GiB free space; creates a unique timestamped directory under `outputs/demo/`; builds the timeline and frontend; and opens backend/browser log files before launching child processes.

- [ ] **Step 4: Launch isolated server and record Chromium correctly**

Follow the current Playwright Python video lifecycle confirmed by Context7:

```python
context = browser.new_context(
    viewport={"width": 1920, "height": 1080},
    record_video_dir=str(run_dir / "playwright"),
    record_video_size={"width": 1920, "height": 1080},
)
page = context.new_page()
page.on("console", lambda message: browser_log.write(
    json.dumps({"type": message.type, "text": message.text}) + "\n"
))
page.on("pageerror", lambda error: browser_log.write(
    json.dumps({"type": "pageerror", "text": str(error)}) + "\n"
))
video = page.video
assert video is not None
page.goto(f"http://127.0.0.1:{port}/?demo=custom10h")
page.get_by_role("button", name="Bắt đầu demo").click()
timeout_ms = int(
    (config.duration_seconds + config.finalization_timeout_seconds + 30) * 1000
)
page.wait_for_function(
    "document.body.dataset.demoState === 'completed'",
    timeout=timeout_ms,
)
trace = page.evaluate("window.__vietAsrDemoTrace")
context.close()
video.save_as(str(raw_webm))
```

Always close the browser context before treating the WebM as complete. Start FastAPI with `DEMO_ENABLED=true`, exact data/duration/gap values, loopback host, and a free port. Terminate the server in `finally`.

- [ ] **Step 5: Render actual playback audio and mux MP4**

Convert recorded pause events to `PlaybackPause`, call `timeline.write_wav(timeline.wav, pauses)`, and compute audio lead delay from the browser trace's epoch timestamp relative to recorder video start. Build this FFmpeg shape:

```bash
ffmpeg -y -i raw.webm -i timeline.wav \
  -filter_complex "[1:a]adelay=2300:all=1,apad[a]" \
  -map 0:v:0 -map "[a]" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 160k -shortest final.mp4
```

The `2300` value above is an example; `build_ffmpeg_command()` substitutes the measured `audio_delay_ms`. Run FFprobe with JSON output and validate width, height, H.264 video, AAC audio, and non-zero duration before writing `run-summary.json` with hashes and completion events.

- [ ] **Step 6: Add the thin command wrapper and runtime documentation**

`scripts/record_custom10h_demo.py` imports `main` from `src.runtime.demo_recorder`. Document the exact one-hour and 15-second smoke commands, expected disk use, output files, interruption behaviour, and the fact that demo routes are disabled by default.

- [ ] **Step 7: Run focused tests and verify GREEN**

```bash
PYTHONPATH="$PWD" .venv/bin/pytest \
  tests/unit/test_demo_recorder.py \
  tests/unit/test_demo_timeline.py \
  tests/unit/test_runtime_layer_rules.py -q
```

- [ ] **Step 8: Commit the recorder**

```bash
git add src/runtime/demo_recorder.py scripts/record_custom10h_demo.py \
  tests/unit/test_demo_recorder.py src/runtime/README.md
git commit -m "feat: record synchronized one-hour demo videos"
```

---

### Task 6: Real-Model Smoke, Full Regression, and One-Hour Recording

**Files:**
- Modify only when a failing verification proves a scoped defect in Tasks 1–5.
- Generate under a timestamped ignored path such as `outputs/demo/20260812-120000/`.

**Interfaces:**
- Consumes: the completed recorder command and current local ASR/recap checkpoints.
- Produces: one verified 15-second MP4 followed by the requested one-hour MP4 and evidence directory.

- [ ] **Step 1: Run the full automated regression before real models**

```bash
RE_EXEC_LD_PATH=1 PYTHONPATH="$PWD" .venv/bin/pytest tests/ -q
pnpm --dir frontend build
pnpm --dir frontend lint
PYTHONPATH=. training-eval-suite/../.venv/bin/pytest \
  training-eval-suite/far_field_asr/tests -q
```

Expected: zero failures. Preserve unrelated dirty files when investigating any failure.

- [ ] **Step 2: Run the 15-second real-model video smoke test**

```bash
LD_LIBRARY_PATH="$PWD/.venv/lib/python3.12/site-packages/onnxruntime/capi:$PWD/.venv/lib/python3.12/site-packages/sherpa_onnx/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
PYTHONPATH="$PWD" .venv/bin/python scripts/record_custom10h_demo.py \
  --duration-seconds 15 \
  --output outputs/demo/custom10h-smoke-15s.mp4
```

Verify from `run-summary.json`: ordered recording IDs, `maxConcurrentAudio == 1`, at least one non-empty utterance, `meeting_completed == true`, `session_closed == true`, and no browser/page errors.

- [ ] **Step 3: Inspect the smoke MP4 and FFprobe evidence**

Run:

```bash
ffprobe -v error -show_streams -show_format -of json \
  outputs/demo/custom10h-smoke-15s.mp4
```

Open one extracted frame and listen to a short audio excerpt. Confirm the visible utterance timing follows audible speech and the final recap is present in the post-roll.

- [ ] **Step 4: Run the requested one-hour recording without acceleration**

```bash
LD_LIBRARY_PATH="$PWD/.venv/lib/python3.12/site-packages/onnxruntime/capi:$PWD/.venv/lib/python3.12/site-packages/sherpa_onnx/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
PYTHONPATH="$PWD" .venv/bin/python scripts/record_custom10h_demo.py \
  --duration-seconds 3600 \
  --output outputs/demo/custom10h-realtime-1h.mp4
```

Monitor backend health, browser demo state, WebSocket backlog, GPU memory, free disk, output growth, and latest ASR diagnostics at intervals no longer than 60 seconds. Do not accelerate playback.

- [ ] **Step 5: Verify the final one-hour evidence before claiming completion**

```bash
test -s outputs/demo/custom10h-realtime-1h.mp4
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height -of json \
  outputs/demo/custom10h-realtime-1h.mp4
ffprobe -v error -select_streams a:0 \
  -show_entries stream=codec_name,duration -of json \
  outputs/demo/custom10h-realtime-1h.mp4
```

Also validate manifest order against the original JSONL line numbers, exact 57,600,000 source samples, no overlapping item ranges, normal session closure, final recap presence, and SHA-256 hashes for all evidence artifacts.

- [ ] **Step 6: Report artifacts without committing generated media**

Provide clickable paths to the MP4, run summary, manifest, FFprobe JSON, browser log, backend log, and diagnostics. Report actual duration, utterance count, recap segment/chunk count, any pauses, and final file size. Do not add `outputs/demo/` to Git.

---

## Plan Self-Review Checklist

- Every approved spec requirement maps to one of Tasks 1–6.
- The timeline interface and names are consistent across backend routes, frontend types, recorder, and tests.
- The sequence is test-first for each production module.
- Normal microphone transport is regression-tested after extracting shared WebSocket logic.
- The 15-second real-model MP4 gates the one-hour run.
- The plan never sorts, randomizes, overlaps, or concurrently plays corpus WAVs.
- The one-hour command runs at 1.0x and waits for both final completion events.
- Generated media remains ignored and user-owned dirty files remain untouched.
