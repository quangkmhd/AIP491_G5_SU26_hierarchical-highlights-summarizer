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
