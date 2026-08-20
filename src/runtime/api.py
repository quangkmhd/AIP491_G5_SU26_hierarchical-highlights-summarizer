from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.service import StreamingOrchestrator
from src.types.schemas import TranscriptIngestionRequest


def create_app() -> FastAPI:
    """Khởi tạo ứng dụng FastAPI Web Server phục vụ dịch vụ Tóm tắt & Phân đoạn Văn bản."""
    app = FastAPI(
        title="Hierarchical Text Summarization Service",
        version="0.1.0",
        description="Dịch vụ phân đoạn chủ đề Multiscale TextTiling và Tóm tắt phân cấp ViT5 & BARTpho",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.state.orchestrator = StreamingOrchestrator()

    @app.post("/api/v1/meetings/process")
    async def process_meeting(payload: TranscriptIngestionRequest) -> JSONResponse:
        """Endpoint xử lý tóm tắt văn bản dạng Batch đồng bộ."""
        try:
            transcript = payload.materialize()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        summary = app.state.orchestrator.process_batch(transcript)
        return JSONResponse(content=summary.model_dump(mode="json"))

    @app.websocket("/ws")
    async def websocket_text_summarization(websocket: WebSocket) -> None:
        """Endpoint WebSocket tiếp nhận câu thoại real-time và trả về các sự kiện tóm tắt."""
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
