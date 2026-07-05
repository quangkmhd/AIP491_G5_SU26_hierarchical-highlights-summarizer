"""ChunkingService -- 8-utterance hierarchical chunking (paper-2 §3.2).

Splits a segment's utterances into Chunks of <= MAX_CHUNK_SIZE = 8 utterances
each. This is the input size for hierarchical_abstractive (deBERTa) which has
a strict 512-token context window.

No overlap in MVP -- paper-2 does not specify an overlap, and the 512-token
context is well above 8 utterances.
"""

from __future__ import annotations

from src.types.segment import Chunk
from src.types.utterance import Utterance


class ChunkingService:
    """Slice a list of utterances into 8-utterance Chunks.

    Usage:
        service = ChunkingService()
        chunks = service.chunk(utterances)
    """

    CHUNK_SIZE: int = Chunk.MAX_CHUNK_SIZE

    def chunk(self, utterances: list[Utterance]) -> list[Chunk]:
        """Slice utterances into ordered Chunks of <= CHUNK_SIZE.

        Empty input raises ValueError. Otherwise returns floor(n / CHUNK_SIZE)
        + (1 if n % CHUNK_SIZE else 0) chunks.
        """
        if not utterances:
            raise ValueError("Cannot chunk empty utterance list")
        chunks: list[Chunk] = []
        for i in range(0, len(utterances), self.CHUNK_SIZE):
            chunk_utts = utterances[i : i + self.CHUNK_SIZE]
            chunks.append(Chunk(utterances=chunk_utts))
        return chunks

    def chunk_indices(self, n_utterances: int) -> list[tuple[int, int]]:
        """Return (start, end_inclusive) index pairs for each chunk.

        Useful for callers that already have the utterances and just want
        the slicing boundaries.
        """
        if n_utterances <= 0:
            raise ValueError(f"n_utterances must be > 0; got {n_utterances}")
        result: list[tuple[int, int]] = []
        for i in range(0, n_utterances, self.CHUNK_SIZE):
            end = min(i + self.CHUNK_SIZE, n_utterances) - 1
            result.append((i, end))
        return result
