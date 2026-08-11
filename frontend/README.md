# Far-Field Meeting Frontend

The React frontend captures the laptop's selected microphone for meetings in which speakers are approximately 1–3 metres away. It uses an `AudioWorklet` at the browser's native sample rate and sends mono Float32 PCM to the backend. Resampling and speech processing remain on the backend so the browser does not discard distant-speech detail.

## Microphone Processing

The browser requests echo cancellation, noise suppression, automatic gain control, and one channel. The `session_start` handshake reports the values actually applied by the browser before queued PCM is released. The client limits its pre-handshake queue to 8 MB and reports a visible failure instead of silently dropping audio.

Only finalized utterances are added to the transcript. During shutdown, the interface enters the **Đang chốt kết quả** state and waits for `session_closed`, allowing the backend to flush the resampler, denoiser, VAD, and ASR tail before the microphone and WebSocket are closed.

## Development

```bash
pnpm install
pnpm dev
```

The development server expects the backend on port `8005` by default. Override this with `VITE_BACKEND_PORT` when needed.

```bash
pnpm build
pnpm lint
```

For the intended room setup, select the laptop's built-in microphone in the transcript toolbar and place the laptop near the centre of the group. Browser microphone permission is required.
