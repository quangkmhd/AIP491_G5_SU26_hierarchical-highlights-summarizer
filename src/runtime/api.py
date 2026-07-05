"""FastAPI server with /api/v1/meetings/stream SSE endpoint."""

from __future__ import annotations

import json
from typing import AsyncIterator

from pathlib import Path

import time
import uuid

from fastapi import FastAPI, HTTPException, Request
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

from src.service import (
    RecapEventType,
    StreamingOrchestrator,
)
from src.types.schemas import TranscriptIngestionRequest
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance


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

    # CORS for local dev: allow the static file:// page to call our API
    # In production this should be restricted to known origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Serve the static UI so the page can be loaded from the same origin
    # (avoids file:// CORS quirks in headless browsers)
    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    if ui_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(ui_dir)), name="ui-static")

        @app.get("/")
        async def index() -> FileResponse:
            index_path = ui_dir / "index.html"
            if not index_path.is_file():
                return FileResponse(content="UI not built", status_code=404)
            return FileResponse(str(index_path))

    app.state.orchestrator = orchestrator or StreamingOrchestrator()

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

    return app


def _materialize(payload: TranscriptIngestionRequest) -> DialogueTranscript:
    """Convert a TranscriptIngestionRequest to a DialogueTranscript."""
    if payload.utterances:
        utts = list(payload.utterances)
    elif payload.flat_texts:
        utts = [
            Utterance(speaker=f"S{i + 1}", text=t, index=i)
            for i, t in enumerate(payload.flat_texts)
        ]
    else:
        raise ValueError("at least one of `utterances` or `flat_texts` must be provided")
    return DialogueTranscript(
        utterances=utts,
        meeting_title=payload.meeting_title,
    )


# Module-level app for uvicorn: `uvicorn src.runtime.api:app`
app = create_app()


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
        return "the model failed to load; check that vibert_checkpoints_vi/cpt_4000.pth exists and is readable"
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
