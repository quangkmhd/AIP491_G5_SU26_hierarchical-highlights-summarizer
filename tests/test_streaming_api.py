import json

from fastapi.testclient import TestClient

from app.main import create_app


class FakeStreamingRecapService:
    def summarize_stream(self, transcript, *, method="both", input_name="frontend-input.md"):
        yield {
            "event": "started",
            "data": {
                "input_name": input_name,
                "method": method,
                "utterance_count": 2,
                "model_targets": [{"model": "fake-model", "base_url": "http://fake"}],
                "results": {},
            },
        }
        yield {
            "event": "method_completed",
            "data": {
                "method": "highlights",
                "result": {"method": "highlights", "notes": [], "tasks": [], "model_runs": []},
            },
        }
        yield {
            "event": "completed",
            "data": {
                "input_name": input_name,
                "method": method,
                "utterance_count": 2,
                "model_targets": [{"model": "fake-model", "base_url": "http://fake"}],
                "langfuse_enabled": False,
                "langfuse_trace_id": "",
                "langfuse_observation_id": "",
                "results": {"highlights": {"method": "highlights", "notes": [], "tasks": [], "model_runs": []}},
            },
        }


def test_summarize_stream_returns_ndjson_events(monkeypatch):
    monkeypatch.setattr("app.main.RecapService", lambda: FakeStreamingRecapService())
    client = TestClient(create_app())

    response = client.post(
        "/api/summarize/stream",
        json={
            "transcript": "Lan(09:00 - 09:01):\nChot viec.\nMinh(09:01 - 09:02):\nEm lam.",
            "method": "highlights",
            "input_name": "stream-test.md",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert [event["event"] for event in events] == ["started", "method_completed", "completed"]
    assert events[1]["data"]["method"] == "highlights"
    assert events[-1]["data"]["results"]["highlights"]["method"] == "highlights"
