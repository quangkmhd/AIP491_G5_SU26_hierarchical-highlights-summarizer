import json

import pytest

from backend.services.meeting_stream_manager import MeetingStreamManager


class FakeDatabase:
    def __init__(self) -> None:
        self.sessions = {
            "a": {"session_id": "a", "title": "Meeting A"},
            "b": {"session_id": "b", "title": "Meeting B"},
        }
        self.utterances: dict[str, list[dict]] = {"a": [], "b": []}
        self.saved: list[tuple[str, dict]] = []

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def get_utterances(self, session_id: str):
        return list(self.utterances[session_id])

    def save_summary(self, session_id: str, summary: dict):
        self.saved.append((session_id, summary))


class FakeWebSocket:
    def __init__(
        self,
        fail_first_utterance: bool = False,
        fail_indexes: set[int] | None = None,
    ) -> None:
        self.sent: list[dict] = []
        self.responses: list[str] = []
        self.closed = False
        self.fail_first_utterance = fail_first_utterance
        self.fail_indexes = fail_indexes or set()

    async def send(self, message: str) -> None:
        payload = json.loads(message)
        self.sent.append(payload)
        if payload["type"] == "utterance":
            if self.fail_first_utterance or payload["index"] in self.fail_indexes:
                self.fail_first_utterance = False
                self.fail_indexes.discard(payload["index"])
                raise ConnectionError("connection dropped")
            self.responses.append(json.dumps({
                "type": "utterance-accepted",
                "session_id": payload["session_id"],
                "index": payload["index"],
            }))
        elif payload["type"] == "flush":
            self.responses.append(json.dumps({
                "type": "meeting-completed",
                "session_id": payload["session_id"],
                "hierarchical_summary": {"segments": [{"title": "Final"}]},
            }))

    async def recv(self) -> str:
        return self.responses.pop(0)

    async def close(self) -> None:
        self.closed = True


class FakeConnector:
    def __init__(self, sockets: list[FakeWebSocket] | None = None) -> None:
        self.sockets = sockets or []
        self.created: list[FakeWebSocket] = []

    async def __call__(self, url: str) -> FakeWebSocket:
        websocket = self.sockets.pop(0) if self.sockets else FakeWebSocket()
        self.created.append(websocket)
        return websocket


def utterance(session_id: str, index: int, text: str) -> dict:
    return {
        "session_id": session_id,
        "speaker_id": "S1",
        "text": text,
        "utterance_index": index,
    }


@pytest.mark.asyncio
async def test_first_publish_starts_stream_and_replays_persisted_utterance() -> None:
    db = FakeDatabase()
    db.utterances["a"] = [utterance("a", 0, "hello")]
    connector = FakeConnector()
    manager = MeetingStreamManager(db, connector=connector, max_retries=1)

    await manager.publish("a", db.utterances["a"][0])

    assert connector.created[0].sent == [
        {"type": "start", "session_id": "a", "meeting_title": "Meeting A"},
        {"type": "utterance", "session_id": "a", "index": 0, "speaker": "S1", "text": "hello"},
    ]


@pytest.mark.asyncio
async def test_sessions_use_independent_connections() -> None:
    db = FakeDatabase()
    db.utterances["a"] = [utterance("a", 0, "alpha")]
    db.utterances["b"] = [utterance("b", 0, "beta")]
    connector = FakeConnector()
    manager = MeetingStreamManager(db, connector=connector, max_retries=1)

    await manager.publish("a", db.utterances["a"][0])
    await manager.publish("b", db.utterances["b"][0])

    assert len(connector.created) == 2
    assert connector.created[0].sent[0]["session_id"] == "a"
    assert connector.created[1].sent[0]["session_id"] == "b"


@pytest.mark.asyncio
async def test_disconnect_reconnects_and_replays_database_in_order() -> None:
    db = FakeDatabase()
    db.utterances["a"] = [
        utterance("a", 0, "zero"),
        utterance("a", 1, "one"),
    ]
    first = FakeWebSocket(fail_first_utterance=True)
    second = FakeWebSocket()
    connector = FakeConnector([first, second])
    manager = MeetingStreamManager(db, connector=connector, max_retries=2, retry_delay=0)

    await manager.publish("a", db.utterances["a"][1])

    replayed = [message for message in second.sent if message["type"] == "utterance"]
    assert [message["index"] for message in replayed] == [0, 1]


@pytest.mark.asyncio
async def test_disconnect_after_prior_ack_reconnects_and_replays_full_database() -> None:
    db = FakeDatabase()
    first_utterance = utterance("a", 0, "zero")
    second_utterance = utterance("a", 1, "one")
    db.utterances["a"] = [first_utterance]
    first = FakeWebSocket(fail_indexes={1})
    second = FakeWebSocket()
    connector = FakeConnector([first, second])
    manager = MeetingStreamManager(db, connector=connector, max_retries=2, retry_delay=0)
    await manager.publish("a", first_utterance)
    db.utterances["a"].append(second_utterance)

    await manager.publish("a", second_utterance)

    replayed = [message for message in second.sent if message["type"] == "utterance"]
    assert [message["index"] for message in replayed] == [0, 1]


@pytest.mark.asyncio
async def test_finish_flushes_and_saves_authoritative_summary() -> None:
    db = FakeDatabase()
    db.utterances["a"] = [utterance("a", 0, "tail")]
    connector = FakeConnector()
    manager = MeetingStreamManager(db, connector=connector, max_retries=1)
    await manager.publish("a", db.utterances["a"][0])

    summary = await manager.finish("a")

    assert connector.created[0].sent[-1] == {"type": "flush", "session_id": "a"}
    assert summary == {"segments": [{"title": "Final"}]}
    assert db.saved == [("a", summary)]
