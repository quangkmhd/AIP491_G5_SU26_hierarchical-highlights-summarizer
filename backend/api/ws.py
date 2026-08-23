"""WebSocket Router for Real-Time Live Audio Streaming & Progress Broadcasting."""

import asyncio
import json
import logging
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/sessions", tags=["WebSocket"])

# Active WebSocket subscriber connections per session_id
active_subscribers: dict[str, list[WebSocket]] = {}


async def broadcast_event(session_id: str, event_data: dict[str, Any]) -> None:
    """Broadcast an event payload to all active WebSocket connections for a session."""
    subscribers = active_subscribers.get(session_id, [])
    if not subscribers:
        return

    dead_sockets = []
    message = json.dumps(event_data, ensure_ascii=False)

    for ws in subscribers:
        try:
            await ws.send_text(message)
        except Exception:
            dead_sockets.append(ws)

    for dead in dead_sockets:
        if dead in subscribers:
            subscribers.remove(dead)


@router.websocket("/{session_id}/stream")
async def websocket_session_stream(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for real-time live audio chunk ingestion and progress broadcasting.
    - Accepts 500ms binary PCM audio streaming chunks or JSON control messages.
    - Emits live updates to UI subscribers.
    """
    await websocket.accept()
    if session_id not in active_subscribers:
        active_subscribers[session_id] = []
    active_subscribers[session_id].append(websocket)

    db = websocket.app.state.db
    orchestrator = websocket.app.state.orchestrator

    logger.info(f"WebSocket client connected for session {session_id}")

    try:
        session = db.get_session(session_id)
        if not session:
            session = db.create_session(session_id=session_id, title=f"Live Stream Session {session_id[:8]}")

        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "status": session["status"],
            "message": "Connected to live pipeline stream.",
        })

        while True:
            # Receive either binary audio chunk (bytes) or text JSON message
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                audio_chunk_bytes = message["bytes"]
                # Forward binary chunk to audio router / processor
                # Broadcast progress state
                await broadcast_event(session_id, {
                    "type": "chunk-received",
                    "session_id": session_id,
                    "bytes_length": len(audio_chunk_bytes),
                })

            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    cmd_type = payload.get("type", "")

                    if cmd_type == "flush" or cmd_type == "finish":
                        await broadcast_event(session_id, {
                            "type": "flush-started",
                            "session_id": session_id,
                        })
                        # Finalize pipeline processing
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from session {session_id}")
    finally:
        if session_id in active_subscribers and websocket in active_subscribers[session_id]:
            active_subscribers[session_id].remove(websocket)
