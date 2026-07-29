# Zipformer Final-Transcript Finalization Design

## Objective

Prevent the streaming Zipformer ASR integration from dropping words at the end
of a VAD-delimited utterance, and make the audio contract diagnosable without
changing the WebSocket event schema.

## Evidence and Scope

The running service on port 8005 loads `sherpa-onnx 1.13.4` with CUDA and all
configured Zipformer and VAD artifacts present. Context7's Sherpa-ONNX
documentation requires an online stream to receive an end-of-input signal and
its streaming example requires 0.4 seconds of zero-valued tail audio before
the final result is read.

A direct CUDA inference check used the same model with short clips from the
available local WAV fixture. Adding the required 0.4-second zero tail changed
the output for 2-, 3-, and 5-second clips; the two-second clip changed from an
empty result to one token. The fixture is non-Vietnamese and is not a WER
benchmark; it is evidence only for recognizer finalization.

This slice changes only the final ASR decode path and its regression coverage.
It does not replace the Zipformer checkpoint, tune model decoding, implement
source separation, or alter the existing WebSocket event payloads.

## Design

`AsrEngine.decode_segment()` will create one `OnlineStream`, accept the VAD
segment at 16 kHz, then append exactly 6,400 zero-valued Float32 samples
(0.4 seconds at 16 kHz). It will call `input_finished()`, decode while the
recognizer reports readiness, and finally return the result text. No audio may
be appended after `input_finished()`.

The existing continuous stream remains a best-effort source of
`partial_utterance` events only. Its output must not be used as the final
utterance. VAD segments continue to be decoded independently, which avoids
crossing utterance boundaries in the final event.

The runtime will validate binary audio before converting it: a non-empty frame
must have a byte length divisible by four, and non-finite Float32 values will
be rejected with a WebSocket close rather than reaching VAD or ONNX Runtime.
It will continue to accept normal Float32 PCM frames exactly as today.

The frontend's existing default already leaves tab audio capture off. This
slice will not alter browser capture settings because browser microphone
quality needs a real Vietnamese recording baseline; enabling noise suppression
is a separate quality-tuning decision.

## Error Handling and Observability

The server will log VAD-segment duration, RMS, peak, and final transcript as
it does now. Invalid PCM is logged with its byte length and rejected before
`numpy.frombuffer()` can raise an unhandled exception. No audio samples or
transcripts are persisted by this change.

## Verification

Unit tests will use a minimal fake online recognizer and stream to prove the
call order: speech samples, 6,400-sample zero tail, `input_finished`, decode
until not ready, then result retrieval. A second test will prove the tail has
the expected Float32 dtype and does not mutate caller-owned audio.

An API/WebSocket test will prove a valid 16-kHz Float32 frame is accepted and
that malformed byte lengths/non-finite samples are rejected before ASR. The
existing fast test suite will then run with `uv run pytest tests/ -q`.

The real-runtime diagnostic will be rerun with
`LD_LIBRARY_PATH=.venv/lib/python3.12/site-packages/onnxruntime/capi:$LD_LIBRARY_PATH`
to verify that `/health` reports `asr_available: true`; this environment is
required by the currently installed project-local sherpa-onnx binary.

## Risks

Zero tail increases each final VAD decode by 0.4 seconds of model input but
does not add wall-clock recording delay because it is supplied immediately
after VAD closes a segment. It should improve end-of-utterance completeness.
The change must not use the partial recognizer stream as a final result because
that stream may include samples after the VAD boundary.
