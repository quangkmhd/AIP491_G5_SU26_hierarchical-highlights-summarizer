# Verification of the Far-Field Meeting ASR Pipeline

# Abstract

This report documents the implementation readiness of the accuracy-first far-field automatic speech recognition (ASR) pipeline for meetings recorded through the built-in laptop microphone at an intended distance of 1–3 metres. The implemented system preserves native-rate microphone audio, applies high-quality stateful resampling and DeepFilterNet enhancement, detects speech using voice activity detection (VAD), assigns persistent speaker profiles, and performs finalized recognition with the `Zipformer-SSL-100h` checkpoint. Automated verification covered unit, integration, end-to-end recovery, TypeScript compilation, production bundling, and static analysis. **The automated suite completed with 318 tests passed, 4 skipped, 2 deselected, and 12 subtests passed; the focused audio path completed with 31 tests passed.** A captured-room benchmark has not yet been supplied, so no word error rate (WER), character error rate (CER), VAD miss rate, or speaker accuracy target is claimed in this report.

**Keywords:** far-field speech recognition, automatic speech recognition (ASR), voice activity detection (VAD), speaker diarization, meeting transcription

# 1 Introduction

The previous browser capture path requested disabled noise suppression, forced a 16 kHz browser audio context where possible, used the deprecated `ScriptProcessorNode`, and performed average-based downsampling in JavaScript. This combination could suppress or distort quiet distant speech before it reached the recognition backend. The revised system targets a laptop placed near the centre of a multi-speaker meeting and prioritizes recognition accuracy over partial-result latency.

The principal objective is to ensure that every valid microphone frame is recoverable and that the final transcript is produced only after the complete enhancement, VAD, speaker, and ASR stages have finalized. The required recognition checkpoint is `models/Zipformer-SSL-100h`, while the source recordings are retained locally for 24 hours by default to support reproducible replay.

# 2 Methodology

## 2.1 Audio Capture and Transport

The frontend uses an AudioWorklet at the browser's native sample rate and requests echo cancellation, noise suppression, automatic gain control, and mono capture. A versioned WebSocket handshake records the settings applied by the browser. PCM frames collected before `session_ready` are bounded in an 8 MB queue; queue exhaustion becomes an explicit failure rather than silent frame loss.

## 2.2 Backend Processing

The backend writes native Float32 PCM directly to WAV before any transformation. Stateful high-quality SoXR resampling converts the continuous timeline to 16 kHz. DeepFilterNet processes 2.5-second windows with 0.3-second context overlap, a 15 dB attenuation limit, and the post-filter disabled. Silero VAD uses a default threshold of 0.35 to improve sensitivity to distant speech. Speaker embeddings are aggregated into per-session centroids, and overlap-processing failures preserve the mixed speech as a fallback instead of discarding it. The ASR model performs one finalized decode for each accepted speaker-labelled segment.

## 2.3 Evaluation Protocol

The project evaluation repository contains a replay manifest schema and deterministic implementations of WER, CER, VAD miss rate, label-invariant speaker error, speaker consistency, clipping rate, real-time factor, and finalization latency. Each replay report includes the full non-secret runtime configuration and SHA-256 fingerprints of the ASR, VAD, and speaker model files. The same decoded WAV samples are supplied to both the current comparison path and the candidate accuracy path.

# 3 Experiments and Results

## 3.1 Automated Verification

Table 1 summarizes the verification completed on 12 August 2026.

| Verification | Result |
| --- | ---: |
| Focused audio unit, integration, and end-to-end tests | **31 passed** |
| Complete project test suite under `tests/` | **318 passed, 4 skipped, 2 deselected, 12 subtests passed** |
| Frontend TypeScript and production build | **Passed** |
| Frontend static analysis | **Passed** |
| Far-field evaluator tests | **5 passed** |
| DeepFilterNet real-model smoke test | **Passed** |
| Zipformer-SSL-100h, Silero VAD, and WeSpeaker CUDA load/decode smoke test | **Passed** |

The end-to-end recovery test transmitted 4,800 native 48 kHz Float32 samples and disconnected without sending `session_end`. The resulting WAV retained the full sample count and native sample rate, and the persisted recording produced a finalized utterance when replayed. The real-model checks loaded `Zipformer-SSL-100h`, Silero VAD, and WeSpeaker with the CUDA provider, finalized a one-second silence input to an empty transcript as expected, and confirmed duration-preserving finite output from DeepFilterNet. These results verify runtime readiness, recoverability, and lifecycle finalization independently of recognition accuracy.

## 3.2 Captured-Room Benchmark Status

No labelled recording from the intended 1–3 metre meeting-room setup is currently present in the evaluator manifest. Consequently, numerical WER, CER, VAD miss rate, speaker error, speaker consistency, real-time factor, and finalization-latency results remain **not measured**. The implementation must not be described as meeting an accuracy target until a labelled room recording is evaluated with `training-eval-suite/far_field_asr/replay.py`.

# 4 Conclusion

The implementation and automated recovery requirements are satisfied: native microphone PCM is preserved, browser-side lossy downsampling has been removed, microphone processing is enabled, finalized ASR output uses `Zipformer-SSL-100h`, and disconnects retain replayable source audio. **The software verification is complete, whereas empirical room-accuracy acceptance remains pending a labelled 1–3 metre recording.** This separation prevents infrastructure readiness from being misreported as measured recognition quality.
