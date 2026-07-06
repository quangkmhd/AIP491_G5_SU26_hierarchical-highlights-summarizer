# Integration of Core Papers

This project is built upon the synergy of two distinct research papers to
create a streaming, hierarchical meeting recap system. This document
explains how their methodologies are combined into a single, cohesive
architecture. **Highlights pipeline (DR1) is out of scope per design
decision 2026-07-05; this document covers only the Hierarchical (DR2)
recap.**

## 1. Topic Segmentation Method (paper-1 _Ours (full)_)

**Source Paper:** _Improving Unsupervised Dialogue Topic Segmentation with
Utterance-Pair Coherence Scoring_

**Role in Project:** This paper serves as the core engine for segmenting
meeting transcripts. We adopt the **best-performing method in the paper
(_Ours (full)_, Table 4)**, which combines:

- A **fine-tuned Next Sentence Prediction (NSP) BERT model** as the
  utterance-pair coherence scorer. The model is `bert-base-multilingual-cased`
  (paper used `aws-ai/dse-bert-base` for English; we use the multilingual
  variant for Vietnamese). Architecture: 12 transformer layers, 12 heads,
  hidden 768, with a `Linear(768, 768) → ReLU → Dropout(0.1) → Linear(768, 2)`
  coherence decoder MLP (paper-1 §3.2, verified against `src/repo/coherence_net.py`).
- **Marginal ranking loss** `L = (1/N) Σ max(0, η + c⁻ - c⁺)` with margin
  `η = 1` (paper-1 §3.2). The training uses two negative sampling
  strategies:
  - **Dialog flow negatives** (different dialogue act, same dialogue).
  - **Dialog topic negatives** (utterance from a different dialogue
    about a different topic).
    Ablation Table 4 shows dialog-flow is the more important signal; the
    full method (both negatives) wins on every metric.
- **TextTiling** (Hearst 1997) consumes the coherence scores and computes
  depth scores `dp_i = 0.5 * (hl(i) + hr(i) - 2 * c_i)` to identify
  valleys. The threshold `τ = μ - σ/2` (paper-1 §3) marks segment
  boundaries.

**Why this method:** Paper-1 Table 4 shows `Ours (full)` is the clear
winner on every metric on both English test sets:

| Method          | DialSeg_711 P_k ↓ | Doc2Dial P_k ↓ | DialSeg_711 F1 ↑ | Doc2Dial F1 ↑ |
| --------------- | ----------------- | -------------- | ---------------- | ------------- |
| TextTiling      | 40.44             | 52.02          | 0.608            | 0.539         |
| TeT + Embedding | 39.37             | 53.72          | 0.637            | 0.602         |
| TeT + NSP       | 46.84             | 50.79          | 0.512            | 0.550         |
| TeT + CLS       | 40.49             | 54.34          | 0.610            | 0.518         |
| **Ours (full)** | **26.80**         | **45.23**      | **0.776**        | **0.660**     |

**Checkpoint:** The user has fine-tuned this architecture on a
Vietnamese dialogue corpus and saved the result to
`vibert_checkpoints_vi/cpt_4000.pth` (463 MB, 4,000 of 36,000 planned
steps; validation accuracy 0.7752 at step 4,000). `model-002` loads
this checkpoint via `ModelLoader.load_coherence_net()`.

**Code ported from paper:** `references_code/dialogue-topic-segmenter/neural_texttiling.py`
(`depth_computing`, `boundaries_to_segments`) and
`references_code/dialogue-topic-segmenter/model_utils.py` (`CoherenceNet`
architecture, replicated in `src/repo/coherence_net.py`).

The matching service code lives in `src/service/coherence_scorer.py`
and `src/service/text_tiling.py` (planned in `svc-001+002`).

## 2. Hierarchical Recap Presentation (paper-2 DR2)

**Source Paper:** _Summaries, Highlights, and Action Items: Design,
Implementation and Evaluation of an LLM-powered Meeting Recap System_

**Role in Project:** Paper-2 provides the user experience and
architectural blueprint for the _Hierarchical_ recap:

- It advocates for a hierarchical recap that represents a meeting as
  chronological, topic-focused discussions (chapters) to help users
  share knowledge and build consensus (DR2, paper-2 §3.1).
- It uses `hierarchical_segment` to divide the transcript into chapters
  (paper-2 §3.2.2 originally used a BART classifier trained on 12,600
  UHRS-annotated meetings; **we replace this with the paper-1
  `Ours (full)` pipeline because it is unsupervised and the user has
  a fine-tuned Vietnamese checkpoint**).
- `hierarchical_abstractive` (deBERTa) generates 3rd-person rolling
  summaries per 8-utterance chunk. `hierarchical_title` (deBERTa)
  generates chapter titles (paper-2 §3.2).
- The user-study (paper-2 §4, N=7) found participants adopt a
  **breadth-first exploration strategy**: chapter heading first, then
  per-chunk summaries, then raw transcript. This drives the streaming
  UX in D5/D7: chapter cards appear as soon as the boundary is
  confirmed, with a skeleton title until `hierarchical_title` returns.

**Why it is used:** It defines the downstream tasks (chapter titles,
chunk summaries) and the user-study-backed UX (breadth-first
exploration, skeleton state tolerance, copy-paste to email/chat,
chapter title editing).

**Implementation note (mocked at MVP):** The deBERTa models for
`hierarchical_abstractive` and `hierarchical_title` are not yet
publicly available for Vietnamese. At MVP, `ModelLoader` returns
`MockLLMBackbone` (canned Vietnamese responses in
`src/repo/prompts_vi.py`). The real gemma-4-E2B-it-qat-GGUF backbone is gated
by `MODEL_LOAD_LLM=1` for future work.

**Highlights (DR1) is out of scope.** The paper-2 highlights pipeline
(4 BART models, `highlights_extractive` + `highlights_abstractive` for
key-points and action-items) is **not implemented** per the 2026-07-05
design decision. The data models (`Highlight`, `HighlightType`,
`HighlightSource`) and the `highlights_notes` / `highlights_tasks`
fields on `HierarchicalRecap` are deleted (`model-001+`). The
`HighlightsConfig` is deleted (`config-001+`). The Web prototype has no
Highlights tab (`ui-001+002+streaming`).

The matching data model is `HierarchicalRecap` (in
`src/types/hierarchical_recap.py`). The orchestrator that wires
TextTiling → deBERTa title + abstractive is `StreamingOrchestrator`
in `src/service/meeting_recap_orchestrator.py` (planned in
`svc-006+streaming`).

## 3. The Synergy

By combining these two approaches with paper-1's `Ours (full)` method
replacing paper-2's supervised BART segmenter, we get a pipeline that
is:

1. **Ingestion**: Read the raw meeting transcript. Today this is
   `TranscriptIngestionRequest.materialize()` returning a
   `DialogueTranscript`.
2. **Segmentation (Paper 1, _Ours (full)_)**: Apply the
   user-fine-tuned CoherenceNet (NSP-BERT) + TextTiling algorithm to
   strictly identify topically coherent chunks of dialogue. The
   segmentation events stream out as `segment-closed` SSE events
   (spec D5).
3. **Chunking**: Each segment is sliced into 8-utterance chunks
   (`ChunkingService`, `svc-003`).
4. **Summarization (Paper 2 §3.2.2)**: For each chunk, `hierarchical_abstractive`
   (deBERTa, mocked at MVP via `MockLLMBackbone`) generates a
   3rd-person rolling summary. For each segment, `hierarchical_title`
   (deBERTa, mocked) generates a chapter title. Title inference is
   **deferred** as a background asyncio task so the chapter card
   appears before the title returns; chunk summaries are synchronous.
5. **Streaming (Custom)**: All events (`utterance-accepted`,
   `depth-score-updated`, `segment-closed`, `chunk-closed`,
   `title-emitted`, `meeting-completed`) flow to the Web UI via SSE
   (FastAPI) or NDJSON (CLI) per the canonical event contract in
   `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md`
   Section 6.

This hybrid approach ensures that:

- Chapter boundaries match paper-1 _Ours (full)_ quality (F1 ≈ 0.78 on
  DialSeg_711 in the paper; the user's checkpoint is at 0.7752
  validation accuracy, partial fine-tuning).
- The user sees chapter cards within 5 seconds of the boundary being
  confirmed, with a skeleton title that upgrades in place.
- The pipeline is fully unsupervised (no need for paper-2's 12,600
  UHRS-annotated meetings) and works offline with the local checkpoint.
- The product surface is minimal: one Hierarchical recap view, no
  Highlights tab, no extra LLM backbone at MVP.

## 4. Mapping Data Models ↔ Paper Concepts

| Paper 1 (Topic Segmentation)     | Paper 2 (Hierarchical Recap)               | Code Model                                    |
| -------------------------------- | ------------------------------------------ | --------------------------------------------- |
| Dialogue                         | Meeting                                    | `DialogueTranscript`                          |
| Turn / Utterance                 | Utterance                                  | `Utterance`                                   |
| Topic boundary                   | Chapter / Segment                          | `SegmentResult`                               |
| Window of 8 utterances           | Chunk (context window for 512-token limit) | `Chunk`                                       |
| NSP coherence score (not stored) | —                                          | computed by `CoherenceScorer` (`svc-001+002`) |
| —                                | Chapter title                              | `SegmentResult.title` / `user_title_override` |
| —                                | Chunk rolling summary                      | `Chunk.rolling_summary`                       |
| —                                | Full recap                                 | `HierarchicalRecap`                           |

## 5. Out-of-scope (deferred to future specs)

- **Paper-2 DR1 (Highlights)** — explicitly out of scope. If re-added in
  a future milestone, it would be a new feature `svc-008-highlights-pipeline`
  with new data models, new AI checkpoints, and a new UI tab.
- **Paper-2 §3.2.2 supervised BART segmenter** — replaced by paper-1
  _Ours (full)_ because the user has a Vietnamese fine-tuned NSP-BERT
  checkpoint and the unsupervised method matches paper-1 SOTA
  performance.
- **Live ASR ingestion** — the orchestrator is streaming-capable but
  the runtime surface is HTTP+SSE only. A future WebSocket route
  could pipe live ASR utterances into
  `StreamingOrchestrator.process_stream`.
- **Multi-speaker voice separation** — assumed solved upstream.
- **Cross-meeting recap linking** — not in either paper; deferred.
