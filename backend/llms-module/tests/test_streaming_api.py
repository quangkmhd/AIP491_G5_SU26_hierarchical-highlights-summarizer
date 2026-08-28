from fastapi.testclient import TestClient

from runtime.api import create_app
from service.summarization_orchestrator import OrchestratorEvent, SummarizationEventType


class FakeBatchOrchestrator:
    summarizer = None


class FakeStreamingOrchestrator:
    def __init__(self) -> None:
        self.accepted: list[tuple[str, str, int]] = []
        self.finalized = False

    def accept_utterance(self, text: str, speaker: str, index: int):
        self.accepted.append((text, speaker, index))
        yield OrchestratorEvent(
            SummarizationEventType.UTTERANCE_ACCEPTED,
            {"index": index, "speaker": speaker, "text": text},
        )

    def flush_and_finalize(self):
        self.finalized = True
        yield OrchestratorEvent(
            SummarizationEventType.MEETING_COMPLETED,
            {"hierarchical_summary": {"segments": []}},
        )


def build_test_app():
    streams: list[FakeStreamingOrchestrator] = []

    def factory() -> FakeStreamingOrchestrator:
        stream = FakeStreamingOrchestrator()
        streams.append(stream)
        return stream

    app = create_app(
        orchestrator=FakeBatchOrchestrator(),
        streaming_orchestrator_factory=factory,
    )
    return app, streams


def test_websocket_connections_have_independent_orchestrators() -> None:
    app, streams = build_test_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as first, client.websocket_connect("/ws") as second:
            first.send_json({"type": "start", "session_id": "meeting-a"})
            second.send_json({"type": "start", "session_id": "meeting-b"})
            first.send_json(
                {"type": "utterance", "session_id": "meeting-a", "index": 0, "speaker": "A", "text": "alpha"}
            )
            second.send_json(
                {"type": "utterance", "session_id": "meeting-b", "index": 0, "speaker": "B", "text": "beta"}
            )

            assert first.receive_json() == {
                "type": "utterance-accepted",
                "session_id": "meeting-a",
                "index": 0,
                "speaker": "A",
                "text": "alpha",
            }
            assert second.receive_json()["session_id"] == "meeting-b"

    assert len(streams) == 2
    assert streams[0].accepted == [("alpha", "A", 0)]
    assert streams[1].accepted == [("beta", "B", 0)]


def test_duplicate_is_acked_without_appending_and_gap_is_rejected() -> None:
    app, streams = build_test_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "start", "session_id": "meeting-a"})
            utterance = {
                "type": "utterance",
                "session_id": "meeting-a",
                "index": 4,
                "speaker": "A",
                "text": "only once",
            }
            websocket.send_json(utterance)
            assert websocket.receive_json()["type"] == "utterance-accepted"

            websocket.send_json(utterance)
            duplicate = websocket.receive_json()
            assert duplicate == {
                "type": "utterance-accepted",
                "session_id": "meeting-a",
                "index": 4,
                "duplicate": True,
            }

            websocket.send_json({**utterance, "index": 6, "text": "gap"})
            error = websocket.receive_json()
            assert error["type"] == "error"
            assert error["code"] == "out-of-order-index"

    assert streams[0].accepted == [("only once", "A", 4)]


def test_flush_returns_one_completed_event() -> None:
    app, streams = build_test_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "start", "session_id": "meeting-a"})
            websocket.send_json(
                {"type": "utterance", "session_id": "meeting-a", "index": 0, "speaker": "A", "text": "tail"}
            )
            websocket.receive_json()
            websocket.send_json({"type": "flush", "session_id": "meeting-a"})
            completed = websocket.receive_json()

    assert completed["type"] == "meeting-completed"
    assert completed["session_id"] == "meeting-a"
    assert streams[0].finalized is True
