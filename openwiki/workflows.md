# 🔄 Core Workflows

The system processed dialogues through two main modes: a real-time event-driven **Async Streaming Pipeline** (used for live SSE browser delivery and command-line NDJSON streams) and **Batch Processing** (ideal for offline, single-iteration pipeline executions).

---

## ⚡ 1. The Async Streaming Pipeline

To conform with the findings of Paper 2 (§4), users explore meeting summaries in a **breadth-first pattern**. Chapter cards should appear in the browser prototype instantly upon boundary confirmation, using skeleton placeholders while heavy generative models calculate summaries and titles in the background.

```
       Utterance Stream
              │
              ▼
    ┌──────────────────────────────────┐
    │   SlidingTextTilingService    │ ── Overlapping windows → local τ threshold
    └──────────────────────────────────┘
              │
              ▼
        Confirmed Boundary
              │
              ▼
      Confirmed Boundary
              │
              ├─────────────────────────────────────────┐
              ▼                                         ▼
   ┌──────────────────────┐                 ┌──────────────────────┐
   │   ChunkingService    │                 │  Assemble Chapters   │
   │ (slice into chunks)  │                 │ (emit closed events) │
   └──────────────────────┘                 └──────────────────────┘
              │                                         │
              ▼                                         ▼
   ┌──────────────────────┐                 ┌──────────────────────┐
   │ SummarizationService │                 │ SummarizationService │
   │ (rolling summaries)  │                 │   (chapter titles)   │
   └──────────────────────┘                 └──────────────────────┘
              │                                         │
              ▼                                         ▼
      [CHUNK_CLOSED]                            [TITLE_EMITTED]
```

### The 5-Event Lifecycle
The orchestrator (`StreamingOrchestrator`) governs five deterministic event types:

1.  `utterance-accepted`: Emitted for every newly processed utterance after the initial index. Carrying the text, index, and speaker payload.
2.  `chunk-closed`: Emitted after ViT5 summarizes a chronological chunk of at most 8 utterances.
3.  `segment-closed`: Emitted after every chunk in the topic has a completed summary.
4.  `title-emitted`: Emitted after BARTpho receives only those ordered summaries joined by ` / ` and generates the topic title.
5.  `meeting-completed`: The terminator event carrying the complete immutable `HierarchicalRecap`.

---

## 📦 2. Batch Processing Pipeline

For background workloads, analytics tasks, or static processing runs, the system exposes a synchronous batch execution entrance through `orchestrator.process_batch(transcript)`. 

### Batch Execution Pipeline Steps

1.  **Ingestion & Serialization**: Dialogues are loaded into memory and wrapped in `DialogueTranscript`.
2.  **Streaming Consumption**: The batch engine runs the `process_stream` async generator internally.
3.  **State Aggregation**: Rather than streaming chunks individually, the engine intercepts the intermediate events, appends chunks into segments, maps title values onto chapters, and accumulates metrics.
4.  **Final Export**: The method captures the `MEETING_COMPLETED` payload and exports a structurally sound `HierarchicalRecap` JSON schema. This single-pass stream consumption model prevents running expensive ML inference twice during file output procedures.
