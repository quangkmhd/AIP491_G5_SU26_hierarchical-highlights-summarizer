# Database Schema

The system has no relational database. Persistence is via local JSON files
under the `data/` and the future `recaps/` directory. This document captures
the *logical* schema (the Pydantic models) so a future agent can plan a
durable store without re-reading every source file.

## Logical Schema (Pydantic v2)

Generated from `src/types/*.py`. Last refreshed 2026-07-04.

### Domain models

| Model | File | Cardinality per meeting |
|-------|------|------------------------|
| `Utterance` | `utterance.py` | 1..5000 (enforced by `DialogueTranscript.MAX_UTTERANCES`) |
| `DialogueTranscript` | `transcript.py` | 1 per request |
| `Chunk` | `segment.py` | <= ceil(segment_length / 8) per segment |
| `SegmentResult` | `segment.py` | variable, determined by TextTiling |
| `Highlight` | `highlight.py` | variable, per-segment or global |
| `HierarchicalRecap` | `hierarchical_recap.py` | 1 per meeting |

### File-system layout (planned)

```
data/
  eval_vi/                     # Ground-truth dialogue topic segmentation
    meeting_committee.json
    ...
  recaps/                      # Generated recap JSON files (planned)
    {meeting_id}/
      recap.json               # HierarchicalRecap.model_dump_json()
      transcript.json          # Source DialogueTranscript (for context lookup)
```

### Field constraints summary

| Field | Constraint |
|-------|------------|
| `Utterance.speaker` | non-empty |
| `Utterance.text` | non-empty |
| `Utterance.index` | >= 0; contiguous 0..N-1 in the parent transcript |
| `Utterance` (whole object) | frozen |
| `Chunk.utterances` | 1..8 items |
| `DialogueTranscript.utterances` | 1..5000 items |
| `DialogueTranscript.utterances[].index` | contiguous 0..N-1 |
| `SegmentResult.utterances_start` | >= 0 |
| `SegmentResult.utterances_end` | >= 0 |
| `SegmentResult.title` | non-empty |
| `Highlight.text` | non-empty |
| `Highlight.type` | one of `KEY_POINT` / `ACTION_ITEM` (wire: `key_point` / `action_item`) |
| `HierarchicalRecap.processing_time_ms` | >= 0 (if set) |

## Notes

- All models inherit from `BaseSchema` (`src/types/_base.py`) which sets
  `extra="forbid"` -- any unknown JSON key in storage is a storage bug, not
  a soft failure.
- UUIDs are stored as canonical hyphenated strings (Pydantic's default
  for `UUID` fields when serialized with `model_dump(mode="json")`).
- Datetimes are stored as ISO-8601 UTC strings.
