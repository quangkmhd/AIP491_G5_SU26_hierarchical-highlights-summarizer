from __future__ import annotations

from src.types.segment import Chunk
from src.types.utterance import Utterance


class ChunkingService:
    """Dịch vụ chia nhỏ các câu thoại thành các khối Chunk (mặc định tối đa 8 câu/khối)."""

    CHUNK_SIZE: int = 8

    def chunk(self, utterances: list[Utterance]) -> list[Chunk]:
        """Phân chia danh sách câu thoại thành các khối Chunk (tối đa 8 câu/khối)."""
        return [
            Chunk(utterances=utterances[i : i + self.CHUNK_SIZE])
            for i in range(0, len(utterances), self.CHUNK_SIZE)
        ]
