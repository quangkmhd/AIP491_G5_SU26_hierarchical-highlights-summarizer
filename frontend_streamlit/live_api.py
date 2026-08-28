"""HTTP operations used by the live-meeting Streamlit view."""

from __future__ import annotations

from typing import Any, Callable

import requests


def finalize_live_session(
    backend_url: str,
    session_id: str,
    post: Callable[..., Any] = requests.post,
) -> dict | None:
    """Finalize one live meeting and return its authoritative summary."""
    response = post(
        f"{backend_url}/api/v1/sessions/{session_id}/finalize",
        timeout=330.0,
    )
    if response.status_code != 200:
        raise RuntimeError(response.text or f"Finalize failed with HTTP {response.status_code}")
    return response.json().get("summary")


def summary_cards(summary: dict | None) -> list[tuple[str, str]]:
    """Normalize batch and streaming summary schemas for the current UI."""
    cards: list[tuple[str, str]] = []
    for segment in (summary or {}).get("segments", []):
        title = segment.get("title") or segment.get("chapter_title") or "Chapter"
        chunk_texts = [
            chunk.get("rolling_summary", "").strip()
            for chunk in segment.get("chunks", [])
            if chunk.get("rolling_summary", "").strip()
        ]
        text = "\n".join(chunk_texts) or segment.get("chunk_summary", "")
        cards.append((title, text))
    return cards
