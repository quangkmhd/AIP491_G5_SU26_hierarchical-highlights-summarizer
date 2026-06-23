"""Tests for the lexical-normalization config fields."""

from app.config import AppSettings


def test_recap_normalize_transcript_defaults_to_false(monkeypatch):
    monkeypatch.delenv("RECAP_NORMALIZE_TRANSCRIPT", raising=False)
    settings = AppSettings()
    assert settings.recap_normalize_transcript is False


def test_recap_normalize_transcript_env_true(monkeypatch):
    monkeypatch.setenv("RECAP_NORMALIZE_TRANSCRIPT", "true")
    settings = AppSettings()
    assert settings.recap_normalize_transcript is True


def test_recap_normalize_model_default(monkeypatch):
    monkeypatch.delenv("RECAP_NORMALIZE_MODEL", raising=False)
    settings = AppSettings()
    assert settings.recap_normalize_model == "gemma4:12b-it-qat"


def test_recap_normalize_model_env(monkeypatch):
    monkeypatch.setenv("RECAP_NORMALIZE_MODEL", "other-model:7b")
    settings = AppSettings()
    assert settings.recap_normalize_model == "other-model:7b"


def test_recap_normalize_base_url_default(monkeypatch):
    monkeypatch.delenv("RECAP_NORMALIZE_BASE_URL", raising=False)
    settings = AppSettings()
    assert settings.recap_normalize_base_url == "http://127.0.0.1:11434"


def test_recap_normalize_base_url_env(monkeypatch):
    monkeypatch.setenv("RECAP_NORMALIZE_BASE_URL", "http://192.168.1.5:11434")
    settings = AppSettings()
    assert settings.recap_normalize_base_url == "http://192.168.1.5:11434"
