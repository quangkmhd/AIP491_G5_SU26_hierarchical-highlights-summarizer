from __future__ import annotations

from src.types.segment import Chunk
from src.types.utterance import Utterance


class ChunkingService:
    """Slice a list of utterances into 8-utterance Chunks."""

    CHUNK_SIZE: int = Chunk.MAX_CHUNK_SIZE

    def chunk(self, utterances: list[Utterance]) -> list[Chunk]:
        """Chia danh sách các câu thoại thành danh sách các khối Chunk (tối đa 8 câu/khối)."""
        if not utterances:
            raise ValueError("Cannot chunk empty utterance list")
        chunks: list[Chunk] = []
        for i in range(0, len(utterances), self.CHUNK_SIZE):
            chunk_utts = utterances[i : i + self.CHUNK_SIZE]
            chunks.append(Chunk(utterances=chunk_utts))
        return chunks

    def chunk_indices(self, n_utterances: int) -> list[tuple[int, int]]:
        """Tính toán cặp chỉ số (bắt đầu, kết thúc) cho từng khối Chunk từ tổng số câu thoại."""
        if n_utterances <= 0:
            raise ValueError(f"n_utterances must be > 0; got {n_utterances}")
        result: list[tuple[int, int]] = []
        for i in range(0, n_utterances, self.CHUNK_SIZE):
            end = min(i + self.CHUNK_SIZE, n_utterances) - 1
            result.append((i, end))
        return result
