from frontend_streamlit.live_api import finalize_live_session


class Response:
    status_code = 200
    text = ""

    def json(self) -> dict:
        return {"status": "success", "summary": {"segments": []}}


def test_frontend_finalize_posts_to_session_endpoint_and_returns_summary() -> None:
    calls: list[tuple[str, float]] = []

    def post(url: str, timeout: float):
        calls.append((url, timeout))
        return Response()

    summary = finalize_live_session("http://gateway:8080", "meeting-1", post=post)

    assert calls == [("http://gateway:8080/api/v1/sessions/meeting-1/finalize", 330.0)]
    assert summary == {"segments": []}
