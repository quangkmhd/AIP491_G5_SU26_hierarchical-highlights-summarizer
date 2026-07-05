# svc-006+streaming — StreamingOrchestrator (Archived)

**Goal:** Wire segmentation + summarization into a 6-event streaming pipeline.

**Result:** StreamingOrchestrator with process_stream() (6 event types) and process_batch() (one-shot). 9 unit tests covering event order, batch-equals-streaming, no-highlights, processing time budget.

**Verification at archive time:** Full suite green (200/200); branch merged.
