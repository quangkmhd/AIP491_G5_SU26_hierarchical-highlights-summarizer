"""HierarchicalSummarizationService -- paper-2 §3.2 deBERTa title + abstractive.

Two methods:
  - title(segment): generates a chapter title (deBERTa hierarchical_title)
  - abstractive(chunk): generates a 3rd-person rolling summary (deBERTa
    hierarchical_abstractive)

At MVP both go through ModelLoader's MockLLMBackbone (canned Vietnamese
responses). The real Vistral-7B-Chat backbone is gated by MODEL_LOAD_LLM=1
(already supported in model-002).
"""

from __future__ import annotations

import json

from src.logging import get_logger
from src.repo.model_loader import ModelLoader
from src.repo.prompts_vi import LLMTask
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance

logger = get_logger("src.service.hierarchical_summarization")


class HierarchicalSummarizationService:
    """Generate chapter titles and chunk rolling summaries.

    Usage:
        service = HierarchicalSummarizationService()
        title = service.title(segment)
        summary = service.abstractive(chunk)
    """

    # Paper-2 spec upper bounds; mock responses comply.
    TITLE_MAX_CHARS: int = 64
    ABSTRACTIVE_MAX_CHARS: int = 256

    def __init__(self, loader: ModelLoader | None = None) -> None:
        self._loader = loader or ModelLoader.instance()
        # Touch the LLM_BACKBONE handle so the mock (or real backbone) is
        # loaded once at construction.
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

    def _extract_title(self, generated: str) -> str:
        try:
            payload = json.loads(generated)
        except json.JSONDecodeError:
            return generated.strip()
        if isinstance(payload, dict):
            title = payload.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        return "none"

    def _extract_summary(self, generated: str) -> str:
        try:
            payload = json.loads(generated)
        except json.JSONDecodeError:
            return generated.strip()
        if isinstance(payload, dict):
            notes = payload.get("notes")
            if isinstance(notes, list) and notes:
                first = notes[0]
                if isinstance(first, dict):
                    summary = first.get("summary")
                    if isinstance(summary, str) and summary.strip():
                        return summary.strip()
        return "none"

    def title(self, segment: SegmentResult) -> str:
        """Generate a short chapter title (Vietnamese, <= 64 chars)."""
        all_utts: list[Utterance] = []
        for chunk in segment.chunks:
            all_utts.extend(chunk.utterances)
        if not all_utts:
            return "Chương trống"
        prompt_text = self._format_utterances(all_utts)
        generated = self._backbone.generate(prompt_text, task=LLMTask.TITLE.value)
        generated = self._extract_title(generated)
        # Truncate to TITLE_MAX_CHARS as a safety net.
        if len(generated) > self.TITLE_MAX_CHARS:
            logger.debug("title truncated chars=%d max=%d", len(generated), self.TITLE_MAX_CHARS)
            generated = generated[: self.TITLE_MAX_CHARS]
        return generated

    def abstractive(self, chunk: Chunk) -> str:
        """Generate a 3rd-person rolling summary for a chunk (<= 256 chars)."""
        if not chunk.utterances:
            return "Đoạn trống"
        prompt_text = self._format_utterances(chunk.utterances)
        generated = self._backbone.generate(prompt_text, task=LLMTask.ABSTRACTIVE.value)
        generated = self._extract_summary(generated)
        if len(generated) > self.ABSTRACTIVE_MAX_CHARS:
            logger.debug(
                "abstractive summary truncated chars=%d max=%d",
                len(generated),
                self.ABSTRACTIVE_MAX_CHARS,
            )
            generated = generated[: self.ABSTRACTIVE_MAX_CHARS]
        return generated

    def abstractive_utterances(self, utterances: list[Utterance]) -> str:
        """Convenience: summarize a flat list of utterances (no Chunk wrapper)."""
        return self.abstractive(Chunk(utterances=utterances))
