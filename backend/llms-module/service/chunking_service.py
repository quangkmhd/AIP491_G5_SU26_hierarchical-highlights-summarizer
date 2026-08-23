from __future__ import annotations

from schemas_dto.segment import Chunk
from schemas_dto.utterance import Utterance


class ChunkingService:
    """Service to split utterances into Chunk blocks (default max 8 utterances/chunk)."""

    CHUNK_SIZE: int = 8

    def chunk(self, utterances: list[Utterance]) -> list[Chunk]:
        """Split a list of utterances into Chunk blocks (max 8 utterances/chunk)."""
        if not utterances:
            raise ValueError("Cannot chunk empty utterance list")
        return [
            Chunk(utterances=utterances[i : i + self.CHUNK_SIZE])
            for i in range(0, len(utterances), self.CHUNK_SIZE)
        ]

    def chunk_indices(self, n_utterances: int) -> list[tuple[int, int]]:
        """Calculate (start_index, end_index) index ranges for each chunk block."""
        if n_utterances <= 0:
            raise ValueError(f"n_utterances must be > 0; got {n_utterances}")
        return [
            (i, min(i + self.CHUNK_SIZE, n_utterances) - 1)
            for i in range(0, n_utterances, self.CHUNK_SIZE)
        ]
