"""Hierarchical chunk summarization and summary-only topic titling."""

from __future__ import annotations

from src.logging import get_logger
from src.repo.model_loader import ModelLoader
from src.repo.seq2seq_inference import (
    BARTphoTopicTitler,
    ChunkSummarizer,
    TopicTitler,
    ViT5ChunkSummarizer,
)
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance

logger = get_logger("src.service.hierarchical_summarization")


class HierarchicalSummarizationService:
    TITLE_INPUT_MAX_CHARS = 1500

    def __init__(
        self,
        chunk_summarizer: ChunkSummarizer | None = None,
        topic_titler: TopicTitler | None = None,
        loader: ModelLoader | None = None,
    ) -> None:
        model_loader = loader or ModelLoader.instance()
        self._chunk_summarizer = chunk_summarizer or ViT5ChunkSummarizer(
            model_loader.load_chunk_summarizer()
        )
        self._topic_titler = topic_titler or BARTphoTopicTitler(
            model_loader.load_topic_titler()
        )

    @staticmethod
    def _format_utterances(utterances: list[Utterance]) -> str:
        return "\n".join(f"- {utterance.speaker}: {utterance.text}" for utterance in utterances)

    def abstractive(self, chunk: Chunk, chapter_number: int = 1, chunk_index: int = 0) -> str:
        if not chunk.utterances:
            return "Đoạn trống"
        return self._chunk_summarizer.summarize(self._format_utterances(chunk.utterances))

    def title(self, segment: SegmentResult, chapter_number: int = 1) -> str:
        summaries = [
            chunk.rolling_summary.strip()
            for chunk in segment.chunks
            if chunk.rolling_summary and chunk.rolling_summary.strip()
        ]
        if not summaries:
            return "Chương trống"
        joined = " / ".join(summaries)
        return self._topic_titler.generate_title(joined[-self.TITLE_INPUT_MAX_CHARS:])

    def abstractive_utterances(self, utterances: list[Utterance]) -> str:
        return self.abstractive(Chunk(utterances=utterances))
