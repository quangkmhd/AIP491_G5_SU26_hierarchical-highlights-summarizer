from backend.main import service_urls_from_env


def test_service_urls_include_llm_websocket_override(monkeypatch) -> None:
    monkeypatch.setenv("SD_URL", "http://sd:9002/diarize")
    monkeypatch.setenv("ASR_URL", "http://asr:9001/transcribe")
    monkeypatch.setenv("LLM_URL", "http://llm:9000/process")
    monkeypatch.setenv("LLM_WS_URL", "ws://llm:9000/ws")

    assert service_urls_from_env() == {
        "sd_url": "http://sd:9002/diarize",
        "asr_url": "http://asr:9001/transcribe",
        "llm_url": "http://llm:9000/process",
        "llm_ws_url": "ws://llm:9000/ws",
    }
