from unittest.mock import AsyncMock, patch

import pytest

from backend.services.pipeline_orchestrator import PipelineOrchestrator


class FakeDatabase:
    def __init__(self) -> None:
        self.utterances: list[dict] = []
        self.statuses: list[str] = []

    def update_session_status(self, session_id: str, status: str, progress: float) -> None:
        self.statuses.append(status)

    def get_utterances(self, session_id: str) -> list[dict]:
        return list(self.utterances)

    def add_utterance(self, **values) -> dict:
        record = dict(values)
        self.utterances.append(record)
        return record

    def get_session(self, session_id: str) -> dict:
        return {"session_id": session_id, "title": "Live", "meeting_type": "online_live"}

    def get_summary(self, session_id: str):
        return None

    def fail_session(self, session_id: str, message: str) -> None:
        self.statuses.append("failed")


class FakeStreamManager:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []
        self.finished: list[str] = []

    async def publish(self, session_id: str, utterance: dict, progress_callback=None) -> None:
        self.published.append((session_id, utterance))

    async def finish(self, session_id: str, progress_callback=None) -> dict:
        self.finished.append(session_id)
        return {"segments": []}


class Response:
    status_code = 200
    text = ""

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def json(self) -> dict:
        return self.payload


class RecordingHttpClient:
    calls: list[str] = []
    flush_segments: list[dict] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url: str, **kwargs) -> Response:
        self.calls.append(url)
        if url.endswith("/flush"):
            return Response({"segments": self.flush_segments})
        return Response({"segments": [{"audio": "segment"}]})


def routed(text: str) -> dict:
    return {
        "speaker_id": "S1",
        "text": text,
        "start_time": 0,
        "end_time": 1,
        "has_overlap": False,
    }


@pytest.mark.asyncio
async def test_live_utterance_is_published_without_http_batch_or_completed_status() -> None:
    db = FakeDatabase()
    streams = FakeStreamManager()
    orchestrator = PipelineOrchestrator(db, stream_manager=streams)
    orchestrator.router.route_diarized_segment = AsyncMock(return_value=[routed("hello")])
    RecordingHttpClient.calls = []

    with patch("backend.services.pipeline_orchestrator.httpx.AsyncClient", RecordingHttpClient):
        result = await orchestrator.process_live_audio_chunk("live-1", b"audio")

    assert [item[1]["text"] for item in streams.published] == ["hello"]
    assert orchestrator.llm_url not in RecordingHttpClient.calls
    assert "completed" not in db.statuses
    assert result["status"] == "recording"


@pytest.mark.asyncio
async def test_finalize_publishes_flushed_tail_before_stream_flush() -> None:
    db = FakeDatabase()
    streams = FakeStreamManager()
    orchestrator = PipelineOrchestrator(db, stream_manager=streams)
    orchestrator.router.route_diarized_segment = AsyncMock(return_value=[routed("tail")])
    RecordingHttpClient.calls = []
    RecordingHttpClient.flush_segments = [{"audio": "tail"}]

    with patch("backend.services.pipeline_orchestrator.httpx.AsyncClient", RecordingHttpClient):
        summary = await orchestrator.finalize_live_session("live-1")

    assert [item[1]["text"] for item in streams.published] == ["tail"]
    assert streams.finished == ["live-1"]
    assert summary == {"segments": []}
    assert orchestrator.llm_url not in RecordingHttpClient.calls
