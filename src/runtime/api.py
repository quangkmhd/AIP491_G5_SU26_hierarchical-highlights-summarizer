"""FastAPI server with /api/v1/meetings/stream SSE endpoint."""

from __future__ import annotations

import json
from typing import AsyncIterator

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from src.service import StreamingOrchestrator
from src.types.schemas import TranscriptIngestionRequest
from src.types.transcript import DialogueTranscript


def create_app(orchestrator: StreamingOrchestrator | None = None) -> FastAPI:
    """Build a FastAPI app with the streaming endpoint wired to `orchestrator`."""
    app = FastAPI(title="Meeting Recap", version="0.1.0")
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
    # Serve the static UI so the page can be loaded from the same origin
    # (avoids file:// CORS quirks in headless browsers)
    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    if ui_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(ui_dir)), name="ui-static")

        @app.get("/")
        async def index() -> FileResponse:
            index_path = ui_dir / "index.html"
            if not index_path.is_file():
                return JSONResponse(
                    content={"detail": "UI not built"}, status_code=404
                )
            return FileResponse(str(index_path))

    app.state.orchestrator = orchestrator or StreamingOrchestrator()

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
    """Convert a TranscriptIngestionRequest to a DialogueTranscript.

    Delegates to the schema's materialize() method which also enforces
    MAX_UTTERANCES and carries language + metadata forward.
    """
    return payload.materialize()


# No eager module-level `app` -- it would trigger the full model-load
# chain (StreamingOrchestrator → CoherenceScorer → NSP checkpoint)
# at import time, breaking every test that touches src.runtime.
#
# Start the server with the --factory flag:
#    uvicorn src.runtime.api:create_app --factory
