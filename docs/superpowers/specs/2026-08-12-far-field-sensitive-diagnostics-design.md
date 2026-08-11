# Far-Field Sensitive Capture and Session Diagnostics Design

## Evidence and Objective

The latest retained 48 kHz recording contains usable distant speech. Direct raw-audio replay with the selected Zipformer produced 13 non-empty utterances and 59 words using a sensitive Silero configuration, whereas the current DeepFilterNet-first production path produced only 5 utterances. The failure is therefore downstream of capture: browser noise suppression followed by DeepFilterNet removes speech that remains recognizable in the source WAV.

The objective is to retain more speech at greater distance and make every subsequent failure attributable from files stored in the shared workspace.

## Processing Design

The default `far_field_sensitive` mode uses native WAV persistence, stateful SoXR HQ resampling, and a pass-through preprocessing stage. Browser echo cancellation, noise suppression, and automatic gain remain enabled. DeepFilterNet remains installed and can be explicitly enabled with `ASR_DENOISER_ENABLED=true` for environments where a labelled replay proves that it helps.

Silero VAD defaults follow the current sherpa-onnx documented example: threshold `0.25`, minimum speech `0.25` seconds, minimum silence `0.5` seconds, and maximum speech `10.0` seconds. Empty ASR decodes remain filtered from transcript output.

## Diagnostic Design

Each retained session writes `data/recordings/<session-id>.diagnostics.jsonl` beside its WAV. Records include:

- `session_start`: native sample rate, browser-applied microphone settings, active denoiser mode, VAD configuration, and model paths;
- `source_frame`: periodic raw PCM sample count, RMS, peak, clipping, and cumulative accepted samples;
- `processed_chunk`: enhanced/pass-through signal metrics and timeline;
- `vad_segment`: boundary, duration, confidence, and signal metrics;
- `asr_result`: speaker, text or empty-result marker, and processing latency;
- `session_end`: retained path, sample totals, utterance totals, and empty-decode totals.

Diagnostics contain no audio samples, credentials, or environment-variable values. They use JSON Lines so a partially written session remains inspectable after an unexpected disconnect. WAV and diagnostic files share the same 24-hour cleanup policy.

## Failure Handling and Verification

Failure to write one diagnostic record is logged but must not interrupt audio processing. A failing regression test will prove that the default factory does not invoke a destructive denoiser. Additional tests verify sensitive VAD defaults, diagnostic lifecycle records, empty ASR visibility, cleanup, and disconnect retention. The latest captured WAV will then be replayed through the revised real-model pipeline and compared with the previous five-utterance result.
