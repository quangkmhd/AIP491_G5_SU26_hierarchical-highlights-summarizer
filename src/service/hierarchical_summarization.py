from __future__ import annotations

import re
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

    @staticmethod
    def _normalize_speaker(speaker: str, speaker_map: dict[str, str]) -> str:
        """Chuẩn hoá nhãn người nói về định dạng 'no.0', 'no.1',... khớp với tập train."""
        spk = speaker.strip()
        if re.match(r"^no\.\d+$", spk):
            return spk
        match = re.match(r"^no(\d+)$", spk, re.IGNORECASE)
        if match:
            return f"no.{match.group(1)}"
        if spk not in speaker_map:
            speaker_map[spk] = f"no.{len(speaker_map)}"
        return speaker_map[spk]

    def _format_utterances(self, utterances: list[Utterance]) -> str:
        """Định dạng danh sách câu thoại dạng 'no.X: Nội dung' cho mô hình tóm tắt."""
        speaker_map: dict[str, str] = {}
        lines: list[str] = []
        for u in utterances:
            norm_spk = self._normalize_speaker(u.speaker, speaker_map)
            lines.append(f"{norm_spk}: {u.text}")
        return "\n".join(lines)

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
