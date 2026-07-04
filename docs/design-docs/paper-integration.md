# Integration of Core Papers

This project is built upon the synergy of two distinct research papers to
create an advanced meeting recap system. This document explains how their
methodologies are combined into a single, cohesive architecture.

## 1. Topic Segmentation Method

**Source Paper:** *Improving Unsupervised Dialogue Topic Segmentation with
Utterance-Pair Coherence Scoring*

**Role in Project:** This paper serves as the core engine for segmenting
meeting transcripts. Instead of relying on simple sliding windows or basic
semantic similarity, it introduces a Neural TextTiling approach:

- We use a fine-tuned Next Sentence Prediction (NSP) BERT model (or a
  CoherenceNet) to measure the "coherence score" between adjacent utterance
  pairs.
- The TextTiling algorithm computes "depth scores" to identify the valleys
  in coherence, which represent semantic shifts (topic boundaries) in the
  conversation.
- **Why it is used:** It provides highly accurate, unsupervised boundaries
  for open-domain dialogues, outperforming standard lexical overlap methods.

The matching code lives in `src/service/coherence_scorer.py` and
`src/service/text_tiling.py` (planned in `svc-001`).

## 2. Hierarchical Recap Presentation

**Source Paper:** *Summaries, Highlights, and Action Items: Design,
Implementation and Evaluation of an LLM-powered Meeting Recap System*

**Role in Project:** This paper provides the user experience and
architectural blueprint for how a meeting should be summarized and
presented.

- It advocates for a "Hierarchical" recap that represents a meeting as
  chronological, topic-focused discussions (Chapters) to help users share
  knowledge and build consensus.
- In the original paper, a basic BERT classifier with sliding windows was
  used for segmentation.
- **Why it is used:** It defines the downstream tasks: once the transcript
  is divided into chapters, we generate chapter titles, rolling summaries,
  and pull out key highlights and action items.

The matching data model is `HierarchicalRecap` (in `src/types/hierarchical_recap.py`).
The orchestrator that wires TextTiling -> deBERTa -> BART is planned in
`svc-002` (`src/service/meeting_recap_orchestrator.py`).

## The Synergy

By combining these two approaches, we replace the weaker segmentation
module from the second paper with the superior, coherence-based unsupervised
segmenter from the first paper.

**The resulting pipeline:**

1. **Ingestion**: Read the raw meeting transcript. Today this is
   `TranscriptIngestionRequest.materialize()` returning a `DialogueTranscript`.
2. **Segmentation (Paper 1)**: Apply the CoherenceNet + TextTiling
   algorithm to strictly identify topically coherent chunks of dialogue.
3. **Summarization (Paper 2)**: Pass these well-defined chunks into
   abstractive summarizers to generate the Hierarchical Minutes (Chapters,
   Titles, Action Items).

This hybrid approach ensures that the chapters presented to the end user
are semantically robust, leading to much higher quality summaries and a
better user experience.

## Layered Implementation Map

| Paper concept | Code home | Layer |
|---------------|-----------|-------|
| Utterance, Transcript, Chunk, Segment, Highlight, Recap | `src/types/` | Types |
| TextTiling config (alpha, window size) | `src/config/` | Config |
| CoherenceNet model, ModelLoader, transcript I/O | `src/repo/` | Repo |
| CoherenceScorer, TextTiling, SegmenterService, MeetingRecapOrchestrator | `src/service/` | Service |
| FastAPI router, CLI | `src/runtime/` | Runtime |
| Web App | `src/ui/` (future) | UI |
