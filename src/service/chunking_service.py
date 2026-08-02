"""ChunkingService -- 8-utterance hierarchical chunking (paper-2 §3.2).

Splits a segment's utterances into Chunks of <= MAX_CHUNK_SIZE = 8 utterances
each. This is the trained input unit for the local ViT5 chunk summarizer, which has
a strict 512-token context window.

No overlap in MVP -- paper-2 does not specify an overlap, and the 512-token
context is well above 8 utterances.
"""

from __future__ import annotations

from src.logging import get_logger
from src.types.segment import Chunk
from src.types.utterance import Utterance

logger = get_logger("src.service.chunking_service")


class ChunkingService:
    """Slice a list of utterances into 8-utterance Chunks.

    Usage:
        service = ChunkingService()
        chunks = service.chunk(utterances)
    """

    CHUNK_SIZE: int = Chunk.MAX_CHUNK_SIZE

    def chunk(self, utterances: list[Utterance]) -> list[Chunk]:
        """Chia danh sách các câu thoại thành danh sách các khối Chunk (tối đa 8 câu/khối)."""
        if not utterances:
            raise ValueError("Cannot chunk empty utterance list")
        chunks: list[Chunk] = []
        for i in range(0, len(utterances), self.CHUNK_SIZE):
            chunk_utts = utterances[i : i + self.CHUNK_SIZE]
            chunks.append(Chunk(utterances=chunk_utts))
        logger.debug(
            "chunking done utterances=%d chunks=%d chunk_size=%d",
            len(utterances),
            len(chunks),
            self.CHUNK_SIZE,
        )
        return chunks

    def chunk_indices(self, n_utterances: int) -> list[tuple[int, int]]:
        """Tính toán cặp chỉ số (bắt đầu, kết thúc) cho từng khối Chunk từ tổng số câu thoại."""
        if n_utterances <= 0:
            raise ValueError(f"n_utterances must be > 0; got {n_utterances}")
        result: list[tuple[int, int]] = []
        for i in range(0, n_utterances, self.CHUNK_SIZE):
            end = min(i + self.CHUNK_SIZE, n_utterances) - 1
            result.append((i, end))
        logger.debug(
            "chunk indices computed utterances=%d chunks=%d chunk_size=%d",
            n_utterances,
            len(result),
            self.CHUNK_SIZE,
        )
        return result
