"""Unit tests for ChunkingService (svc-003)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.service import ChunkingService
from src.types.segment import Chunk
from src.types.utterance import Utterance


def _u(i: int, text: str = "x") -> Utterance:
    return Utterance(speaker="S1", text=text, index=i)


class ChunkingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ChunkingService()

    def test_chunk_size_constant(self) -> None:
        self.assertEqual(self.service.CHUNK_SIZE, 8)
        self.assertEqual(Chunk.MAX_CHUNK_SIZE, 8)

    def test_exactly_8_returns_1_chunk(self) -> None:
        utts = [_u(i) for i in range(8)]
        chunks = self.service.chunk(utts)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0].utterances), 8)

    def test_30_utterances_returns_4_chunks(self) -> None:
        utts = [_u(i) for i in range(30)]
        chunks = self.service.chunk(utts)
        self.assertEqual(len(chunks), 4)
        self.assertEqual([len(c.utterances) for c in chunks], [8, 8, 8, 6])

    def test_7_utterances_returns_1_chunk(self) -> None:
        utts = [_u(i) for i in range(7)]
        chunks = self.service.chunk(utts)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0].utterances), 7)

    def test_1_utterance_returns_1_chunk(self) -> None:
        utts = [_u(0)]
        chunks = self.service.chunk(utts)
        self.assertEqual(len(chunks), 1)

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.service.chunk([])

    def test_chunk_indices_30_utt(self) -> None:
        pairs = self.service.chunk_indices(30)
        self.assertEqual(pairs, [(0, 7), (8, 15), (16, 23), (24, 29)])

    def test_chunk_indices_8_utt(self) -> None:
        self.assertEqual(self.service.chunk_indices(8), [(0, 7)])

    def test_chunk_indices_zero_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.service.chunk_indices(0)

    def test_chunks_preserve_order(self) -> None:
        utts = [_u(i, text=f"u{i}") for i in range(16)]
        chunks = self.service.chunk(utts)
        self.assertEqual([u.text for u in chunks[0].utterances], [f"u{i}" for i in range(8)])
        self.assertEqual([u.text for u in chunks[1].utterances], [f"u{i}" for i in range(8, 16)])

    def test_chunks_have_unique_ids(self) -> None:
        utts = [_u(i) for i in range(20)]
        chunks = self.service.chunk(utts)
        ids = [c.chunk_id for c in chunks]
        self.assertEqual(len(ids), len(set(ids)))
