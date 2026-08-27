from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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

    @app.post("/api/v1/meetings/process")
    async def process_meeting(payload: TranscriptIngestionRequest) -> JSONResponse:
        """Endpoint xử lý tóm tắt văn bản dạng Batch đồng bộ."""
        transcript = payload.materialize()
        summary = StreamingOrchestrator().process_batch(transcript)
        return JSONResponse(content=summary.model_dump(mode="json"))

    @app.websocket("/ws")
    async def websocket_text_summarization(websocket: WebSocket) -> None:
        """Endpoint WebSocket tiếp nhận câu thoại real-time và trả về các sự kiện tóm tắt."""
        await websocket.accept()
        ws_orchestrator = StreamingOrchestrator()

        try:
            while True:
                payload = await websocket.receive_json()

                if payload.get("type") == "flush":
                    for evt in ws_orchestrator.flush_and_finalize():
                        await websocket.send_json(evt)
                    break

                text = payload.get("text", "").strip()
                if not text:
                    continue

                for evt in ws_orchestrator.accept_utterance(
                    text=text,
                    speaker=payload.get("speaker", "no.0"),
                    index=payload.get("index"),
                ):
                    await websocket.send_json(evt)

        except (WebSocketDisconnect, Exception):
            pass

    return app
