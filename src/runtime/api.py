from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from src.service import StreamingOrchestrator
from src.types.schemas import TranscriptIngestionRequest
from src.types.transcript import DialogueTranscript


def create_app(
    orchestrator: StreamingOrchestrator | None = None,
) -> FastAPI:
    """Khởi tạo và cấu hình ứng dụng FastAPI web server phục vụ dịch vụ Tóm tắt & Phân đoạn Văn bản."""
    app = FastAPI(title="Hierarchical Text Summarization Service", version="0.1.0")

    # Middleware tạo request-id và đo thời gian xử lý HTTP request.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        try:
            response = await call_next(request)
        except Exception as e:  # noqa: BLE001
            return JSONResponse(
                status_code=500,
                content={
                    "error": type(e).__name__,
                    "message": str(e) or type(e).__name__,
                    "request_id": rid,
                },
            )
        response.headers["X-Request-Id"] = rid
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.state.orchestrator = orchestrator or StreamingOrchestrator()

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "status_code": exc.status_code,
                "detail": exc.detail,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=422,
            content={
                "error": "RequestValidationError",
                "status_code": 422,
                "detail": json.loads(json.dumps(exc.errors(), default=str)),
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=400,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
            },
        )

    @app.post("/api/v1/meetings/process")
    async def process_meeting(payload: TranscriptIngestionRequest) -> JSONResponse:
        """Synchronous batch text summarization endpoint."""
        try:
            transcript = _materialize(payload)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        summary = app.state.orchestrator.process_batch(transcript)
        return JSONResponse(content=summary.model_dump(mode="json"))

    @app.post("/api/v1/meetings/stream")
    async def stream_meeting(payload: TranscriptIngestionRequest) -> EventSourceResponse:
        """Streaming SSE text summarization endpoint."""
        try:
            transcript = _materialize(payload)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        async def event_generator() -> AsyncIterator[dict]:
            for event in app.state.orchestrator.process_stream(transcript):
                yield {"event": event.type.value, "data": json.dumps(event.data, default=str)}
            yield {"event": "end", "data": "{}"}

        return EventSourceResponse(event_generator())

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "service": "Text Summarization & Topic Segmentation",
        }

    @app.websocket("/ws")
    async def websocket_text_summarization(websocket: WebSocket):
        """Streaming text WebSocket endpoint for real-time utterance ingestion and topic recap."""
        await websocket.accept()
        ws_orchestrator = app.state.orchestrator
        ws_orchestrator.reset_incremental()
        utterance_counter = 0

        try:
            while True:
                message = await websocket.receive_text()
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                    continue

                msg_type = payload.get("type", "utterance")

                if msg_type in {"flush", "session_end", "complete"}:
                    for evt in ws_orchestrator.flush_and_finalize():
                        await websocket.send_json({"type": evt.type.value, **evt.data})
                    break

                text = payload.get("text", "").strip()
                if not text:
                    continue

                speaker = payload.get("speaker", "Speaker 01")
                idx = payload.get("index", utterance_counter)
                utterance_counter += 1

                for evt in ws_orchestrator.accept_utterance(text=text, speaker=speaker, index=idx):
                    await websocket.send_json({"type": evt.type.value, **evt.data})

        except WebSocketDisconnect:
            pass
        except Exception:
            pass

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
