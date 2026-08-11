"""FastAPI server with /api/v1/meetings/stream SSE and /ws WebSocket ASR endpoints."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import AsyncIterator

import numpy as np
from pydantic import ValidationError

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
from src.types.audio import AudioSessionStart

def _ensure_ld_library_path() -> None:
    venv_site = (
        Path(__file__).resolve().parent.parent.parent
        / ".venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    ort_capi = venv_site / "onnxruntime" / "capi"
    sherpa_lib = venv_site / "sherpa_onnx" / "lib"

    needed = [str(ort_capi), str(sherpa_lib)]
    existing_ld = os.environ.get("LD_LIBRARY_PATH", "")

    missing = [p for p in needed if p not in existing_ld and Path(p).exists()]
    if missing and "RE_EXEC_LD_PATH" not in os.environ:
        new_ld = ":".join(missing + ([existing_ld] if existing_ld else []))
        os.environ["LD_LIBRARY_PATH"] = new_ld
        os.environ["RE_EXEC_LD_PATH"] = "1"
        os.execv(sys.executable, [sys.executable] + sys.argv)

_ensure_ld_library_path()

try:
    from src.config.asr import AsrConfig
    from src.service.audio_preprocessor import DeepFilterNetEnhancer, PassthroughEnhancer
    from src.service.asr_engine import AsrEngine
    from src.service.far_field_pipeline import DefaultFarFieldSessionFactory
    _ASR_AVAILABLE = True
except ImportError:
    _ASR_AVAILABLE = False


def _decode_pcm_float32(payload: bytes) -> np.ndarray:
    """Giải mã và kiểm định một khung dữ liệu âm thanh PCM Float32 từ WebSocket."""
    if len(payload) % np.dtype(np.float32).itemsize:
        raise ValueError("audio frame byte length must be a multiple of 4 for Float32 PCM")
    chunk = np.frombuffer(payload, dtype=np.float32)
    if not np.isfinite(chunk).all():
        raise ValueError("audio frame must contain only finite Float32 PCM samples")
    return chunk


def create_app(
    orchestrator: StreamingOrchestrator | None = None,
    audio_session_factory: object | None = None,
) -> FastAPI:
    """Khởi tạo và cấu hình ứng dụng FastAPI web server với các endpoint streaming và WebSocket ASR."""
    app = FastAPI(title="Meeting Recap", version="0.1.0")
    logger = get_logger("src.runtime.api")

    # Middleware tạo request-id và đo thời gian xử lý HTTP request.
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
                # Lỗi chưa được xử lý: ghi log cùng ngữ cảnh request và trả về lỗi 500
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

    # Cấu hình CORS cho phép các domain gọi API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    # Phục vụ giao diện người dùng tĩnh (React build từ thư mục frontend/dist)
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="frontend-assets")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(str(dist_dir / "index.html"))

    app.state.orchestrator = orchestrator or StreamingOrchestrator()

    # --- Khởi tạo công cụ ASR ---
    asr_engine_instance = None
    resolved_audio_factory = audio_session_factory
    if resolved_audio_factory is None and _ASR_AVAILABLE:
        try:
            asr_config = AsrConfig()
            asr_engine_instance = AsrEngine(asr_config)
            if asr_config.denoiser_enabled:
                enhancer = DeepFilterNetEnhancer(
                    atten_lim_db=asr_config.denoiser_atten_lim_db,
                    post_filter=asr_config.denoiser_post_filter,
                )
                logger.info("DeepFilterNet enabled for microphone audio")
            else:
                enhancer = PassthroughEnhancer()
                logger.info("Far-field sensitive mode: preserving browser-processed microphone audio")
            recordings_root = Path(__file__).resolve().parents[2] / "data" / "recordings"
            resolved_audio_factory = DefaultFarFieldSessionFactory(
                config=asr_config,
                asr=asr_engine_instance,
                enhancer=enhancer,
                recordings_root=recordings_root,
            )
            logger.info("Accuracy-first audio pipeline loaded successfully")
        except Exception as e:
            logger.warning("Audio pipeline not available: %s. WebSocket /ws will be disabled.", e)
    else:
        logger.info("sherpa-onnx not installed; ASR WebSocket endpoint disabled.")
    app.state.asr_engine = asr_engine_instance
    app.state.audio_session_factory = resolved_audio_factory

    logger.info(
        "AI System Initialized:\n"
        "  [Title Model]   : BARTpho Topic Titler\n"
        "  [Summary Model] : ViT5 Chunk Summarizer\n"
        "  [ASR Engine]    : Zipformer SSL 100h Transducer chunk-32\n"
        "  [Speaker Model] : WeSpeaker ResNet34 LM\n"
        "  [VAD Engine]    : Silero VAD\n"
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[no-untyped-def]
        # Đối với lỗi 4xx, trả về thông tin chi tiết kèm gợi ý hướng xử lý (fix)
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
        # Lỗi LoggableError mang theo thông tin gợi ý sửa lỗi fix/hint tương ứng
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
        # Chuyển đổi ngoại lệ ValueError từ tầng service thành HTTP status 400
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
            "asr_available": app.state.audio_session_factory is not None,
        }

    @app.websocket("/ws")
    async def websocket_asr_endpoint(websocket: WebSocket):
        """Native mic -> persistence -> enhancement -> VAD -> speaker -> final ASR."""
        if app.state.audio_session_factory is None:
            logger.error("Audio pipeline not initialized -- rejecting WebSocket client.")
            await websocket.close(code=1011, reason="audio pipeline not initialized")
            return

        await websocket.accept()
        logger.info("WebSocket client connected: %s", websocket.client)
        audio_session = None
        retain_recording = True
        session_closed_sent = False
        ws_orchestrator = app.state.orchestrator
        ws_orchestrator.reset_incremental()

        async def send_audio_events(events) -> None:  # type: ignore[no-untyped-def]
            for event in events:
                payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else dict(event)
                await websocket.send_json(payload)
                if payload.get("type") != "utterance" or not payload.get("text"):
                    continue
                for evt in ws_orchestrator.accept_utterance(
                    text=payload["text"],
                    speaker=payload.get("speaker", "Unknown Speaker"),
                    index=int(payload["id"]) - 1,
                ):
                    if evt.type != RecapEventType.UTTERANCE_ACCEPTED:
                        await websocket.send_json({
                            "type": evt.type.value,
                            **evt.data,
                        })

        async def finalize_session() -> None:
            nonlocal session_closed_sent
            if audio_session is None or session_closed_sent:
                return
            await send_audio_events(await asyncio.to_thread(audio_session.flush))
            for evt in ws_orchestrator.flush_and_finalize():
                await websocket.send_json({"type": evt.type.value, **evt.data})
            audio_session.close(retain=retain_recording)
            await websocket.send_json({
                "type": "session_closed",
                "session_id": audio_session.session_id,
                "retained": retain_recording,
            })
            session_closed_sent = True

        try:
            first = await websocket.receive()
            if "text" not in first:
                await websocket.send_json({
                    "type": "pipeline_error",
                    "stage": "protocol",
                    "message": "session_start JSON is required before PCM audio",
                })
                await websocket.close(code=1003, reason="session_start required")
                return
            try:
                start = AudioSessionStart.model_validate_json(first["text"])
            except (ValidationError, ValueError, TypeError) as exc:
                await websocket.send_json({
                    "type": "pipeline_error",
                    "stage": "protocol",
                    "message": str(exc),
                })
                await websocket.close(code=1003, reason="invalid session_start")
                return

            audio_session = app.state.audio_session_factory.create(start)
            await websocket.send_json({
                "type": "session_ready",
                "protocol_version": 1,
                "session_id": audio_session.session_id,
                "source_sample_rate": start.sample_rate,
                "sample_rate": 16000,
                "settings": start.settings.model_dump(mode="json"),
            })

            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                if "bytes" in message:
                    try:
                        chunk = _decode_pcm_float32(message["bytes"])
                    except ValueError as exc:
                        logger.warning("Rejecting invalid WebSocket PCM frame: %s", exc)
                        await websocket.close(code=1003, reason="invalid Float32 PCM audio")
                        break
                    if len(chunk) > 0:
                        events = await asyncio.to_thread(audio_session.push, chunk)
                        await send_audio_events(events)

                elif "text" in message:
                    try:
                        payload = json.loads(message["text"])
                        if payload.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                        elif payload.get("type") == "session_end":
                            retain_recording = bool(payload.get("retain", True))
                            await finalize_session()
                            return
                    except (json.JSONDecodeError, AttributeError):
                        await websocket.send_json({
                            "type": "pipeline_error",
                            "stage": "protocol",
                            "message": "invalid control message",
                        })

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected.")
        except Exception as exc:
            logger.exception("Error in WebSocket handler: %s", exc)
        finally:
            if audio_session is not None and not session_closed_sent:
                try:
                    audio_session.flush()
                except Exception:
                    logger.exception("Error flushing audio session on disconnect.")
                finally:
                    audio_session.close(retain=True)
            logger.info("WebSocket audio session cleaned up")

    return app


def _materialize(payload: TranscriptIngestionRequest) -> DialogueTranscript:
    """Chuyển đổi yêu cầu nạp bản ghi thành đối tượng DialogueTranscript."""
    return payload.materialize()


# No eager module-level `app` -- it would trigger model loading
# at import time, breaking every test that touches src.runtime.
#
# Start the server with the --factory flag:
#    uvicorn src.runtime.api:create_app --factory


def _suggest_fix_for_http(exc: HTTPException) -> str:
    """Đề xuất gợi ý xử lý tương ứng cho các mã lỗi HTTP 4xx/5xx."""
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
    """Xác định mức độ log phù hợp cho từng đường dẫn request để tránh rác log."""
    if request.method == "GET" and request.url.path in {"/", "/favicon.ico"}:
        return 10
    if request.method == "GET" and request.url.path.startswith("/static/"):
        return 10
    return 20


def _suggest_fix_for_value_error(exc: ValueError) -> str:
    """Đề xuất hướng xử lý cho các lỗi ValueError xuất phát từ dữ liệu đầu vào."""
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
    """Đề xuất hướng sửa lỗi cho các ngoại lệ kiểm định dữ liệu Pydantic/FastAPI."""
    text = " ".join(str(err.get("msg", "")) for err in exc.errors()).lower()
    if "utterances" in text or "flat_texts" in text or "at least one" in text:
        return "provide at least one non-empty item in `utterances` or `flat_texts`"
    if "missing" in text:
        return "add the missing required JSON field shown in response.detail"
    if "extra" in text:
        return "remove unknown JSON fields or check the request schema"
    return "check response.detail and update the JSON body to match the API schema"
