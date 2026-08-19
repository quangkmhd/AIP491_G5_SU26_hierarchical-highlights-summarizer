from __future__ import annotations

from src.types.segment import Chunk
from src.types.utterance import Utterance


class ChunkingService:
    """Dịch vụ chia nhỏ các câu thoại thành các khối Chunk (mặc định tối đa 8 câu/khối)."""

    CHUNK_SIZE: int = 8

    def chunk(self, utterances: list[Utterance]) -> list[Chunk]:
        """Phân chia danh sách câu thoại thành các khối Chunk (tối đa 8 câu/khối)."""
        if not utterances:
            raise ValueError("Cannot chunk empty utterance list")
        return [
            Chunk(utterances=utterances[i : i + self.CHUNK_SIZE])
            for i in range(0, len(utterances), self.CHUNK_SIZE)
        ]

    def chunk_indices(self, n_utterances: int) -> list[tuple[int, int]]:
        """Tính toán khoảng chỉ số (bắt đầu, kết thúc) cho từng khối câu thoại."""
        if n_utterances <= 0:
            raise ValueError(f"n_utterances must be > 0; got {n_utterances}")
        return [
            (i, min(i + self.CHUNK_SIZE, n_utterances) - 1)
            for i in range(0, n_utterances, self.CHUNK_SIZE)
        ]
