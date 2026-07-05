# svc-003 — Hierarchical Chunking (Archived)

**Goal:** Slice segment utterances into 8-utterance Chunks for hierarchical_abstractive.

**Result:** ChunkingService.chunk(utterances) -> list[Chunk], with chunk_indices() helper. 11 unit tests.

**Verification at archive time:** Full suite green; branch merged.
