"""FastAPI server with /api/v1/meetings/stream SSE and /ws WebSocket ASR endpoints."""

from __future__ import annotations

import json
from typing import AsyncIterator

from pathlib import Path

import time
import uuid

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from src.logging import (
    LoggableError,
    get_logger,
    log_error_with_fix,
    request_context,
)
from src.service import StreamingOrchestrator, RecapEventType
from src.types.schemas import TranscriptIngestionRequest
from src.types.transcript import DialogueTranscript

try:
    import numpy as np
    from src.config.asr import AsrConfig
    from src.service.asr_engine import AsrEngine
    _ASR_AVAILABLE = True
except ImportError:
    _ASR_AVAILABLE = False


def create_app(orchestrator: StreamingOrchestrator | None = None) -> FastAPI:
    """Build a FastAPI app with the streaming endpoint wired to `orchestrator`."""
    app = FastAPI(title="Meeting Recap", version="0.1.0")
    logger = get_logger("src.runtime.api")

    # Request-id + timing middleware. Tags every log call within a request
    # with a request_id (taken from the X-Request-Id header if the client
    # sent one, otherwise generated) and an `event` tag identifying the
    # HTTP method + path.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        event = f"{request.method} {request.url.path}"
        with request_context(request_id=rid, event=event):
            t0 = time.perf_counter()
            request_log_level = _request_log_level(request)
            logger.log(request_log_level, "request start")
            try:
                response = await call_next(request)
            except Exception as e:  # noqa: BLE001
                # Unhandled error: log with request context, surface as 500
                log_error_with_fix(
                    logger, e,
                    fix="check server logs for the traceback; report a bug if reproducible",
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": type(e).__name__,
                        "message": str(e) or type(e).__name__,
                        "request_id": rid,
                    },
                )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            response.headers["X-Request-Id"] = rid
            logger.log(
                request_log_level,
                "request done status=%d elapsed_ms=%.1f",
                response.status_code,
                elapsed_ms,
            )
            return response

    # CORS: local development permits any origin so the static file://
    # page can call the API.  In production this must be an explicit
    # allowlist — see FastAPI docs (cors.md): wildcard + credentials
    # is rejected, and `["*"]` exposes every browser-trusted origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    # Serve the static UI -- prefer the React frontend build if available,
    # otherwise fall back to the legacy src/ui directory.
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    if dist_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="frontend-assets")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(str(dist_dir / "index.html"))
    elif ui_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(ui_dir)), name="ui-static")

        @app.get("/")
        async def index() -> FileResponse:  # type: ignore[no-redef]
            index_path = ui_dir / "index.html"
            if not index_path.is_file():
                return JSONResponse(
                    content={"detail": "UI not built"}, status_code=404
                )
            return FileResponse(str(index_path))

    app.state.orchestrator = orchestrator or StreamingOrchestrator()

    # --- ASR Engine initialization ---
    asr_engine_instance = None
    if _ASR_AVAILABLE:
        try:
            asr_config = AsrConfig()
            asr_engine_instance = AsrEngine(asr_config)
            logger.info("ASR engine loaded successfully")
        except Exception as e:
            logger.warning("ASR engine not available: %s. WebSocket /ws will be disabled.", e)
    else:
        logger.info("sherpa-onnx not installed; ASR WebSocket endpoint disabled.")
    app.state.asr_engine = asr_engine_instance

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[no-untyped-def]
        # For 4xx we expect callers to fix something; surface a `fix` field
        # so they know what to do.
        fix = _suggest_fix_for_http(exc)
        logger.warning("HTTPException status=%d detail=%s", exc.status_code, exc.detail, extra={"fix": fix, "status_code": exc.status_code})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "status_code": exc.status_code,
                "detail": exc.detail,
                "fix": fix,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):  # type: ignore[no-untyped-def]
        fix = _suggest_fix_for_validation(exc)
        logger.warning(
            "request validation failed errors=%d",
            len(exc.errors()),
            extra={"fix": fix, "status_code": 422},
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "RequestValidationError",
                "status_code": 422,
                "detail": json.loads(json.dumps(exc.errors(), default=str)),
                "fix": fix,
            },
        )

    @app.exception_handler(LoggableError)
    async def loggable_error_handler(request: Request, exc: LoggableError):  # type: ignore[no-untyped-def]
        # LoggableError carries its own fix; surface it in the response.
        log_error_with_fix(logger, exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
                "fix": exc.fix,
                "hint": exc.hint,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):  # type: ignore[no-untyped-def]
        # Service-layer ValueErrors (e.g. empty transcript) become 400 with a fix
        fix = _suggest_fix_for_value_error(exc)
        log_error_with_fix(logger, exc, fix=fix)
        return JSONResponse(
            status_code=400,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
                "fix": fix,
            },
        )

    @app.post("/api/v1/meetings/process")
    async def process_meeting(payload: TranscriptIngestionRequest) -> JSONResponse:
        """Synchronous batch endpoint. Returns the full HierarchicalRecap."""
        try:
            transcript = _materialize(payload)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        recap = app.state.orchestrator.process_batch(transcript)
        return JSONResponse(content=recap.model_dump(mode="json"))

    @app.post("/api/v1/meetings/stream")
    async def stream_meeting(payload: TranscriptIngestionRequest) -> EventSourceResponse:
        """Streaming SSE endpoint. Yields the 6 event types in order."""
        try:
            transcript = _materialize(payload)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        async def event_generator() -> AsyncIterator[dict]:
            for event in app.state.orchestrator.process_stream(transcript):
                yield {"event": event.type.value, "data": json.dumps(event.data, default=str)}
            # SSE terminator
            yield {"event": "end", "data": "{}"}

        return EventSourceResponse(event_generator())

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "asr_available": app.state.asr_engine is not None,
        }

    @app.websocket("/ws")
    async def websocket_asr_endpoint(websocket: WebSocket):
        """Realtime mic -> VAD -> ASR -> Speaker -> TextTiling -> Recap pipeline.

        Wire protocol (copied from viet_iter3_inference streaming backend):
          Client -> Server: binary Float32 PCM, 16 kHz mono (no header).
          Client -> Server: text "ping"   -> {"type":"pong"}
          Server -> Client: text JSON
              -> {"type":"utterance", ...}
              -> {"type":"segment-closed", ...}
              -> {"type":"chunk-closed", ...}
              -> {"type":"title-emitted", ...}
              -> {"type":"meeting-completed", ...}
        """
        if app.state.asr_engine is None:
            logger.error("ASR engine not initialized -- rejecting WebSocket client.")
            await websocket.close(code=1011, reason="ASR engines not initialized")
            return

        await websocket.accept()
        logger.info("WebSocket client connected: %s", websocket.client)

        asr = app.state.asr_engine
        vad = asr.create_vad()
        ws_orchestrator = StreamingOrchestrator()
        ws_orchestrator.reset_incremental()

        registered_speakers: dict[str, np.ndarray] = {}
        tail: np.ndarray = np.array([], dtype=np.float32)
        utterance_id = 0

        async def process_speech_segment(seg_audio: np.ndarray) -> None:
            """Decode one speech segment, identify speaker, feed orchestrator."""
            nonlocal utterance_id
            utterance_id += 1
            duration = len(seg_audio) / 16000.0

            speaker_name = asr.identify_speaker(seg_audio, registered_speakers)
            text = asr.decode_segment(seg_audio)
            logger.info(
                "ASR Segment #%d: speaker=%s text='%s'",
                utterance_id, speaker_name, text,
            )

            if text:
                await websocket.send_json({
                    "type": "utterance",
                    "id": utterance_id,
                    "text": text,
                    "duration": round(duration, 2),
                    "speaker": speaker_name,
                })

                for evt in ws_orchestrator.accept_utterance(
                    text=text,
                    speaker=speaker_name,
                    index=utterance_id - 1,
                ):
                    if evt.type != RecapEventType.UTTERANCE_ACCEPTED:
                        await websocket.send_json({
                            "type": evt.type.value,
                            **evt.data,
                        })

        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                if "bytes" in message:
                    chunk = np.frombuffer(message["bytes"], dtype=np.float32)
                    tail = np.concatenate([tail, chunk])
                    while len(tail) >= asr.vad_window_size:
                        vad.accept_waveform(tail[:asr.vad_window_size])
                        tail = tail[asr.vad_window_size:]

                    while not vad.empty():
                        seg = vad.front
                        samples = np.asarray(seg.samples, dtype=np.float32)
                        vad.pop()
                        if len(samples) < int(0.3 * 16000):
                            continue
                        await process_speech_segment(samples)

                elif "text" in message:
                    try:
                        payload = json.loads(message["text"])
                        if payload.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                    except (json.JSONDecodeError, AttributeError):
                        pass

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected.")
        except Exception as exc:
            logger.exception("Error in WebSocket handler: %s", exc)
        finally:
            try:
                vad.flush()
                while not vad.empty():
                    seg = vad.front
                    samples = np.asarray(seg.samples, dtype=np.float32)
                    vad.pop()
                    if len(samples) < int(0.3 * 16000):
                        continue
                    await process_speech_segment(samples)
            except Exception:
                logger.exception("Error flushing VAD on close.")

            try:
                for evt in ws_orchestrator.flush_and_finalize():
                    try:
                        await websocket.send_json({
                            "type": evt.type.value,
                            **evt.data,
                        })
                    except Exception:
                        pass
            except Exception:
                logger.exception("Error finalizing recap on close.")

            logger.info("WebSocket cleaned up (total %d segments).", utterance_id)

    return app


def _materialize(payload: TranscriptIngestionRequest) -> DialogueTranscript:
    """Convert a TranscriptIngestionRequest to a DialogueTranscript.

    Delegates to the schema's materialize() method which also enforces
    MAX_UTTERANCES and carries language + metadata forward.
    """
    return payload.materialize()


# No eager module-level `app` -- it would trigger model loading
# at import time, breaking every test that touches src.runtime.
#
# Start the server with the --factory flag:
#    uvicorn src.runtime.api:create_app --factory


def _suggest_fix_for_http(exc: HTTPException) -> str:
    """Map common 4xx status codes to actionable fix suggestions."""
    if exc.status_code == 422:
        return "check the request body matches the schema; see response.detail for field errors"
    if exc.status_code == 400:
        return str(exc.detail) if exc.detail else "check the request payload"
    if exc.status_code == 404:
        return "check the URL path; the resource may not exist"
    if exc.status_code == 413:
        return "split the request into smaller batches (limit is 5000 utterances per transcript)"
    if exc.status_code == 503:
        return "the model failed to load; check the runtime logs for the model loader error"
    return f"client error {exc.status_code}: review the response detail and retry"


def _request_log_level(request: Request) -> int:
    """Keep static asset access logs out of INFO-level operational output."""
    if request.method == "GET" and request.url.path in {"/", "/favicon.ico"}:
        return 10
    if request.method == "GET" and request.url.path.startswith("/static/"):
        return 10
    return 20


def _suggest_fix_for_value_error(exc: ValueError) -> str:
    """Map common ValueError messages to fix suggestions."""
    msg = str(exc).lower()
    if "empty" in msg and ("utterance" in msg or "transcript" in msg):
        return "provide at least one utterance in `utterances` or `flat_texts`"
    if "max_utterances" in msg or "exceeds" in msg:
        return "split the transcript into smaller batches; max 5000 utterances per request"
    if "flat_texts" in msg and "utterances" in msg:
        return "provide either `utterances` or `flat_texts`, not both"
    if "flat_texts" in msg or "utterances" in msg:
        return "provide at least one of `utterances` or `flat_texts`"
    if "cutoff policy" in msg:
        return "use one of: 'mean', 'mean+2std', 'depth_knee'"
    return "check the request payload against the API schema"


def _suggest_fix_for_validation(exc: RequestValidationError) -> str:
    """Map FastAPI/Pydantic request validation errors to actionable fixes."""
    text = " ".join(str(err.get("msg", "")) for err in exc.errors()).lower()
    if "utterances" in text or "flat_texts" in text or "at least one" in text:
        return "provide at least one non-empty item in `utterances` or `flat_texts`"
    if "missing" in text:
        return "add the missing required JSON field shown in response.detail"
    if "extra" in text:
        return "remove unknown JSON fields or check the request schema"
    return "check response.detail and update the JSON body to match the API schema"
