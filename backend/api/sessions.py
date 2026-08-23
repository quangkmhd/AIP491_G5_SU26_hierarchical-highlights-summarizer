"""REST API Router for Session Management & Processing."""

import asyncio
from typing import Any, Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_and_process_session(
    request: Request,
    background_tasks: BackgroundTasks,
    title: Optional[str] = Form(None),
    meeting_type: str = Form("offline_upload"),
    file: Optional[UploadFile] = File(None),
) -> dict[str, Any]:
    """Create a new session and trigger background 3-stage pipeline processing."""
    db = request.app.state.db
    orchestrator = request.app.state.orchestrator

    audio_bytes: bytes = b""
    filename = "uploaded_audio.wav"

    if file and file.filename:
        filename = file.filename
        audio_bytes = await file.read()

    session_rec = db.create_session(
        title=title or f"Meeting Session ({filename})",
        audio_source=filename if file else "live_stream",
        meeting_type=meeting_type,
    )
    sid = session_rec["session_id"]

    if audio_bytes:
        background_tasks.add_task(
            orchestrator.process_audio_file,
            session_id=sid,
            audio_bytes=audio_bytes,
            filename=filename,
        )

    return {
        "status": "success",
        "session": session_rec,
        "message": "Session created and pipeline started." if audio_bytes else "Session created.",
    }


@router.get("", response_model=dict[str, Any])
def list_sessions(request: Request) -> dict[str, Any]:
    """List all meeting sessions."""
    db = request.app.state.db
    sessions = db.get_all_sessions()
    return {
        "total": len(sessions),
        "sessions": sessions,
    }


@router.get("/{session_id}", response_model=dict[str, Any])
def get_session_details(request: Request, session_id: str) -> dict[str, Any]:
    """Query session status, progress percentage, and list of transcribed utterances."""
    db = request.app.state.db
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )

    utterances = db.get_utterances(session_id)
    summary = db.get_summary(session_id)

    return {
        "session": session,
        "utterances": utterances,
        "summary": summary["hierarchical_json"] if summary else None,
    }


@router.get("/{session_id}/summary", response_model=dict[str, Any])
def get_session_summary(request: Request, session_id: str) -> dict[str, Any]:
    """Retrieve final hierarchical summary JSON for a completed session."""
    db = request.app.state.db
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )

    summary = db.get_summary(session_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary for session {session_id} is not ready or failed.",
        )

    return {
        "session_id": session_id,
        "status": session["status"],
        "summary": summary["hierarchical_json"],
        "processing_time_ms": summary.get("processing_time_ms"),
    }
