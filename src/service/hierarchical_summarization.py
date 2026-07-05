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

from src.repo.model_loader import ModelLoader
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance


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

    def _format_utterances(self, utterances: list[Utterance]) -> str:
        return "\n".join(f"- {u.speaker}: {u.text}" for u in utterances)

    def title(self, segment: SegmentResult) -> str:
        """Generate a short chapter title (Vietnamese, <= 64 chars)."""
        all_utts: list[Utterance] = []
        for chunk in segment.chunks:
            all_utts.extend(chunk.utterances)
        if not all_utts:
            return "Chương trống"
        prompt_text = self._format_utterances(all_utts)
        generated = self._backbone.generate(prompt_text, task="title")
        # Truncate to TITLE_MAX_CHARS as a safety net.
        if len(generated) > self.TITLE_MAX_CHARS:
            generated = generated[: self.TITLE_MAX_CHARS]
        return generated

    def abstractive(self, chunk: Chunk) -> str:
        """Generate a 3rd-person rolling summary for a chunk (<= 256 chars)."""
        if not chunk.utterances:
            return "Đoạn trống"
        prompt_text = self._format_utterances(chunk.utterances)
        generated = self._backbone.generate(prompt_text, task="abstractive")
        if len(generated) > self.ABSTRACTIVE_MAX_CHARS:
            generated = generated[: self.ABSTRACTIVE_MAX_CHARS]
        return generated

    def abstractive_utterances(self, utterances: list[Utterance]) -> str:
        """Convenience: summarize a flat list of utterances (no Chunk wrapper)."""
        return self.abstractive(Chunk(utterances=utterances))
