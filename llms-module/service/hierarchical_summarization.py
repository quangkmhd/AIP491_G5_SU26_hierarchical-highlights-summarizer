from __future__ import annotations

from typing import Any

from src.repo.model_loader import ModelLoader
from src.repo.seq2seq_inference import (
    BARTphoTopicTitler,
    ViT5ChunkSummarizer,
)
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance


class HierarchicalSummarizationService:
    """Hierarchical summarization service: Chunk summarization (ViT5) & Chapter titling (BARTpho)."""

    TITLE_INPUT_MAX_CHARS: int = 1500

    def __init__(
        self,
        chunk_summarizer: Any = None,
        topic_titler: Any = None,
        loader: ModelLoader | None = None,
    ) -> None:
        """Initialize ViT5 chunk summarizer and BARTpho topic titler models."""
        model_loader = loader or ModelLoader()
        self._chunk_summarizer = chunk_summarizer or ViT5ChunkSummarizer(
            model_loader.load_chunk_summarizer()
        )
        self._topic_titler = topic_titler or BARTphoTopicTitler(
            model_loader.load_topic_titler()
        )

    def _format_utterances(self, utterances: list[Utterance]) -> str:
        """Format a list of utterances into 'Speaker: Content' lines for summarization model input."""
        return "\n".join(f"{u.speaker}: {u.text}" for u in utterances)

    def abstractive(self, chunk: Chunk) -> str:
        """Generate an abstractive summary for a Chunk block using ViT5."""
        if not chunk.utterances:
            return ""
        return self._chunk_summarizer.summarize(self._format_utterances(chunk.utterances))

    def title(self, segment: SegmentResult) -> str:
        """Generate a chapter title from chunk summaries of a segment using BARTpho."""
        summaries = [
            c.rolling_summary.strip()
            for c in segment.chunks
            if c.rolling_summary and c.rolling_summary.strip()
        ]
        if not summaries:
            return ""
        joined = " / ".join(summaries)
        return self._topic_titler.generate_title(joined[-self.TITLE_INPUT_MAX_CHARS:])

    def abstractive_utterances(self, utterances: list[Utterance]) -> str:
        """Summarize a list of Utterance objects directly."""
        return self.abstractive(Chunk(utterances=utterances))
