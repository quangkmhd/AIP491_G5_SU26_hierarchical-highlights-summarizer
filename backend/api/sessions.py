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

    await orchestrator.reset_diarization_session()

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

    return {"status": "success", "summary": summary}


@router.post("/{session_id}/audio", response_model=dict[str, Any])
async def process_live_audio_chunk(
    request: Request,
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Receive live recorded mic audio frame, run diarization, ASR, and update session."""
    db = request.app.state.db
    orchestrator = request.app.state.orchestrator

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio chunk received.",
        )

    background_tasks.add_task(
        orchestrator.process_audio_file,
        session_id=session_id,
        audio_bytes=audio_bytes,
        filename=file.filename or "live_chunk.wav",
    )

    return {
        "status": "success",
        "message": f"Live audio frame ({len(audio_bytes)} bytes) queued for processing.",
    }


@router.delete("/{session_id}", response_model=dict[str, Any])
def delete_session(request: Request, session_id: str) -> dict[str, Any]:
    """Delete a meeting session and its associated transcripts and summaries."""
    db = request.app.state.db
    deleted = db.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )
    return {"status": "success", "message": f"Session {session_id} deleted."}


@router.put("/{session_id}", response_model=dict[str, Any])
def update_session(request: Request, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Update meeting session metadata (e.g. title)."""
    db = request.app.state.db
    title = payload.get("title")
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title cannot be empty.",
        )
    updated = db.update_session_title(session_id, title)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )
    return {"status": "success", "session": db.get_session(session_id)}
