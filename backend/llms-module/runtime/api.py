import json
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from repo.model_loader import BARTPHO_MODEL_PATH, PROJECT_ROOT, VIT5_MODEL_PATH
from service import StreamingOrchestrator
from schemas_dto.schemas import TranscriptIngestionRequest


def create_app(
    orchestrator: StreamingOrchestrator | None = None,
) -> FastAPI:
    """Initialize FastAPI Web Server for Text Summarization & Segmentation service."""
    app = FastAPI(
        title="Hierarchical Text Summarization Service",
        version="0.1.0",
        description="Multiscale TextTiling topic segmentation and ViT5 & BARTpho hierarchical summarization service",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.state.orchestrator = orchestrator or StreamingOrchestrator()

    @app.get("/health")
    def health_check(response: Response) -> dict[str, Any]:
        """Health check endpoint verifying the presence of local model checkpoints."""
        vit5_exists = (VIT5_MODEL_PATH / "config.json").is_file()
        bartpho_exists = (BARTPHO_MODEL_PATH / "config.json").is_file()

        summarizer = getattr(app.state.orchestrator, "summarizer", None)
        vit5_loaded = (
            summarizer is not None
            and getattr(summarizer, "_chunk_summarizer", None) is not None
            and getattr(summarizer._chunk_summarizer, "handle", None) is not None
        )
        bartpho_loaded = (
            summarizer is not None
            and getattr(summarizer, "_topic_titler", None) is not None
            and getattr(summarizer._topic_titler, "handle", None) is not None
        )

        is_healthy = vit5_exists and bartpho_exists
        if not is_healthy:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        def _to_rel_path(p: Path) -> str:
            try:
                return p.relative_to(PROJECT_ROOT).as_posix()
            except ValueError:
                return str(p)

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "Text Summarization & Topic Segmentation",
            "models": {
                "vit5_chunk_summarizer": {
                    "path": _to_rel_path(VIT5_MODEL_PATH),
                    "exists": vit5_exists,
                    "loaded": vit5_loaded,
                },
                "bartpho_topic_titler": {
                    "path": _to_rel_path(BARTPHO_MODEL_PATH),
                    "exists": bartpho_exists,
                    "loaded": bartpho_loaded,
                },
            },
        }

    @app.post("/api/v1/meetings/process")
    async def process_meeting(payload: TranscriptIngestionRequest) -> JSONResponse:
        """Synchronous batch meeting transcript summarization endpoint."""
        try:
            transcript = payload.materialize()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        summary = app.state.orchestrator.process_batch(transcript)
        return JSONResponse(content=summary.model_dump(mode="json"))

    @app.websocket("/ws")
    async def websocket_text_summarization(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time utterance ingestion and summarization event streaming."""
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
