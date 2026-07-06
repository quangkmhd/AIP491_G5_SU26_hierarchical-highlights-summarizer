"""HierarchicalSummarizationService -- paper-2 §3.2 title + abstractive.

Two methods:
  - title(segment): generates a chapter title
  - abstractive(chunk): generates a 3rd-person rolling summary

Both methods fill the Vietnamese prompt templates from prompts_vi.py,
call the LLM backbone with JSON-constrained decoding, and parse the
response into typed pydantic models.
"""

from __future__ import annotations

import json
import logging
from typing import List

from pydantic import BaseModel, Field

from src.logging import get_logger
from src.repo.model_loader import ModelLoader
from src.repo.prompts_vi import (
    HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
    HIERARCHIC_TITLE_PROMPT_VI,
    LLMTask,
    SYSTEM_PROMPT_VI,
)
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance

logger = get_logger("src.service.hierarchical_summarization")


# -- Pydantic models for LLM JSON output ---------------------------------

class TitleResponse(BaseModel):
    """JSON schema for the hierarchical_title task."""

    title: str = Field(description="Tiêu đề chapter ngắn gọn bằng tiếng Việt")
    one_line_summary: str = Field(description="Một câu tóm tắt chapter bằng tiếng Việt")


class AbstractiveNote(BaseModel):
    """JSON schema for a single chunk note in the hierarchical_abstractive task."""

    chunk_id: str = Field(description="ID của chunk")
    summary: str = Field(description="Ghi chú factual 1-3 câu bằng tiếng Việt")
    contains_key_point: bool = Field(default=False)
    contains_action_item: bool = Field(default=False)


class AbstractiveResponse(BaseModel):
    """JSON schema for the hierarchical_abstractive task."""

    notes: List[AbstractiveNote] = Field(description="Danh sách ghi chú theo chunk")


class HierarchicalSummarizationService:
    """Generate chapter titles and chunk rolling summaries.

    Usage:
        service = HierarchicalSummarizationService()
        title = service.title(segment)
        summary = service.abstractive(chunk)
    """

    TITLE_MAX_CHARS: int = 64
    ABSTRACTIVE_MAX_CHARS: int = 256

    def __init__(self, loader: ModelLoader | None = None) -> None:
        self._loader = loader or ModelLoader.instance()
        self._handle = self._loader.load_llm_backbone()
        self._backbone = self._handle.model
        logger.info(
            "summarization backbone ready kind=%s device=%s checkpoint=%s",
            self._handle.kind.value,
            self._handle.device,
            self._handle.checkpoint_path or "mock",
        )

    def _format_utterances(self, utterances: list[Utterance]) -> str:
        return "\n".join(f"- {u.speaker}: {u.text}" for u in utterances)

    def title(self, segment: SegmentResult, chapter_number: int = 1) -> str:
        """Generate a short chapter title (Vietnamese, <= 64 chars)."""
        all_utts: list[Utterance] = []
        for chunk in segment.chunks:
            all_utts.extend(chunk.utterances)
        if not all_utts:
            return "Chương trống"

        prompt = HIERARCHIC_TITLE_PROMPT_VI.format(
            input_name="inline",
            chapter_number=chapter_number,
            segment_utterances=self._format_utterances(all_utts),
        )
        generated = self._backbone.generate(prompt, task=LLMTask.TITLE.value)

        try:
            payload = TitleResponse.model_validate_json(generated)
            title = payload.title.strip()
        except Exception as e:
            logger.warning("title JSON parse failed, falling back: %s", e)
            title = generated.strip()

        if len(title) > self.TITLE_MAX_CHARS:
            title = title[: self.TITLE_MAX_CHARS]
        return title if title else "none"

    def abstractive(self, chunk: Chunk, chapter_number: int = 1, chunk_index: int = 0) -> str:
        """Generate a 3rd-person rolling summary for a chunk (<= 256 chars)."""
        if not chunk.utterances:
            return "Đoạn trống"

        chunk_id_str = str(chunk.chunk_id)
        prompt = HIERARCHIC_ABSTRACTIVE_PROMPT_VI.format(
            input_name="inline",
            chapter_number=chapter_number,
            required_chunk_ids=chunk_id_str,
            prompt_chunks=f"--- chunk_id: {chunk_id_str} ---\n{self._format_utterances(chunk.utterances)}",
        )
        generated = self._backbone.generate(prompt, task=LLMTask.ABSTRACTIVE.value)

        try:
            payload = AbstractiveResponse.model_validate_json(generated)
            if payload.notes:
                summary = payload.notes[0].summary.strip()
            else:
                summary = "none"
        except Exception as e:
            logger.warning("abstractive JSON parse failed, falling back: %s", e)
            summary = generated.strip()

        if len(summary) > self.ABSTRACTIVE_MAX_CHARS:
            summary = summary[: self.ABSTRACTIVE_MAX_CHARS]
        return summary if summary else "none"

    def abstractive_utterances(self, utterances: list[Utterance]) -> str:
        """Convenience: summarize a flat list of utterances (no Chunk wrapper)."""
        return self.abstractive(Chunk(utterances=utterances))
