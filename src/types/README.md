# Types Layer

This directory defines the core data structures and types used throughout the system.

## Role
- Contains data models, schemas, and type definitions (e.g., Pydantic models, dataclasses, TypedDicts, Enums).
- Serves as the shared language across all layers.

## Rules
- **No dependencies**: This layer MUST NOT import anything from `config`, `repo`, `service`, or `runtime`.
- No business logic or external I/O operations are allowed here.

## Core Models to Implement
- `Utterance`: Represents a single sentence/statement in a transcript.
- `DialogueTranscript`: Represents the sequence of utterances.
- `SegmentResult`: Represents a detected topic segment (e.g., boundary index, label).
