# Design Docs Index

Use this index as the discoverable map of design history.

## Accepted

- `core-beliefs.md`: agent-first operating beliefs and durable project norms
- `system-architecture.md`: definitive architecture for the Hierarchical Meeting
  Recap system (container diagram, sequence diagram, API contracts, NFRs)
- `models-and-roadmap.md`: data models (Types layer inventory) and the
  layered implementation roadmap
- `paper-integration.md`: how the two source papers combine into a single
  pipeline (NSP BERT TextTiling -> deBERTa/BART recap)

## Proposed

- `[add new proposals here when they arise]`

## Deprecated

- `[move old or superseded design docs here with replacement links]`

## Maintenance Rules

- Every design doc should have an owner or update trigger.
- Remove stale docs or mark them deprecated instead of letting them drift.
- Link active execution plans to the design docs they depend on.
- When a feature (`model-001`, `svc-001`, ...) becomes passing, update the
  matching entry in `models-and-roadmap.md` and link the evidence file.
