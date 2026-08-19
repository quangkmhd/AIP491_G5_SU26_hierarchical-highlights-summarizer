from __future__ import annotations

from typing import Any

from src.repo.model_loader import ModelLoader, get_model_loader
from src.repo.seq2seq_inference import (
    BARTphoTopicTitler,
    ViT5ChunkSummarizer,
)
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance


class HierarchicalSummarizationService:
    TITLE_INPUT_MAX_CHARS = 1500

    def __init__(
        self,
        chunk_summarizer: Any = None,
        topic_titler: Any = None,
        loader: ModelLoader | None = None,
    ) -> None:
        """Khởi tạo dịch vụ tóm tắt phân cấp và sinh tiêu đề."""
        model_loader = loader or get_model_loader()
        self._chunk_summarizer = chunk_summarizer or ViT5ChunkSummarizer(
            model_loader.load_chunk_summarizer()
        )
        self._topic_titler = topic_titler or BARTphoTopicTitler(
            model_loader.load_topic_titler()
        )

    def _format_utterances(self, utterances: list[Utterance]) -> str:
        """Định dạng danh sách câu thoại thành chuỗi văn bản đầu vào cho mô hình tóm tắt."""
        return "\n".join(f"{utterance.speaker}: {utterance.text}" for utterance in utterances)

    def abstractive(self, chunk: Chunk, chapter_number: int = 1, chunk_index: int = 0) -> str:
        """Sinh câu tóm tắt trừu tượng cho một khối câu thoại."""
        if not chunk.utterances:
            return "Đoạn trống"
        return self._chunk_summarizer.summarize(self._format_utterances(chunk.utterances))

    def title(self, segment: SegmentResult, chapter_number: int = 1) -> str:
        """Sinh tiêu đề cho phân đoạn chủ đề từ danh sách các câu tóm tắt khối."""
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
        """Tóm tắt trực tiếp từ danh sách các đối tượng Utterance."""
        return self.abstractive(Chunk(utterances=utterances))
