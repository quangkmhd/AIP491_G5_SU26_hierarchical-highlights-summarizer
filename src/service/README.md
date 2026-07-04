# Service Layer

This directory contains the core algorithms and domain logic.

## Role
- Implements the topic segmentation algorithms (Coherence scoring, TextTiling, depth computing, threshold finding).
- Coordinates model inference and algorithm flow.
- Coordinates the downstream summarization and recap logic.

## Rules
- **Dependency Limit**: Can only import from `repo`, `config`, and `types` layers.
- MUST NOT import from the `runtime` layer.
- Must remain independent of the specific delivery mechanism (CLI, web server, API).

## Core Modules to Implement
- `coherence_scorer.py`: Calculates coherence scores for utterance pairs.
- `text_tiling.py`: Implements TextTiling algorithm logic (depth scores, thresholding, segment boundaries).
- `segmenter_service.py`: Orchestrates the segmentation process by retrieving inputs, scoring coherence, applying TextTiling, and producing segment boundaries.
