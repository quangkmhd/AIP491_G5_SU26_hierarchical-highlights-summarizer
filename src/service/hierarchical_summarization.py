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
    """Dịch vụ tóm tắt phân cấp gồm: Tóm tắt khối (ViT5) & Sinh tiêu đề chương (BARTpho)."""

    TITLE_INPUT_MAX_CHARS: int = 1500

    def __init__(
        self,
        chunk_summarizer: Any = None,
        topic_titler: Any = None,
    ) -> None:
        """Khởi tạo 2 mô hình ViT5 tóm tắt và BARTpho sinh tiêu đề."""
        loader = ModelLoader()
        self._chunk_summarizer = chunk_summarizer or ViT5ChunkSummarizer(
            loader.load_chunk_summarizer()
        )
        self._topic_titler = topic_titler or BARTphoTopicTitler(
            loader.load_topic_titler()
        )

    def _format_utterances(self, utterances: list[Utterance]) -> str:
        """Định dạng danh sách câu thoại dạng 'Người nói: Nội dung' cho mô hình tóm tắt."""
        return "\n".join(f"{u.speaker}: {u.text}" for u in utterances)

    def abstractive(self, chunk: Chunk) -> str:
        """Sinh câu tóm tắt trừu tượng cho một khối câu thoại Chunk bằng ViT5."""
        if not chunk.utterances:
            return ""
        return self._chunk_summarizer.summarize(self._format_utterances(chunk.utterances))

    def title(self, segment: SegmentResult) -> str:
        """Sinh tiêu đề chương từ các câu tóm tắt khối của phân đoạn bằng BARTpho."""
        summaries = [
            c.rolling_summary.strip()
            for c in segment.chunks
            if c.rolling_summary and c.rolling_summary.strip()
        ]
        if not summaries:
            return ""
        joined = " / ".join(summaries)
        return self._topic_titler.generate_title(joined[-self.TITLE_INPUT_MAX_CHARS:])
