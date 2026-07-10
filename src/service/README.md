# Service Layer

This directory contains the core algorithms and domain logic.

## Role
- Implements the topic segmentation algorithms (Sliding TextTiling: BoW + cosine + multi-scale depth).
- Coordinates model inference and algorithm flow.
- Coordinates the downstream summarization and recap logic.

## Rules
- **Dependency Limit**: Can only import from `repo`, `config`, and `types` layers.
- MUST NOT import from the `runtime` layer.
- Must remain independent of the specific delivery mechanism (CLI, web server, API).

## Core Modules to Implement
- `text_tiling.py`: Implements Sliding TextTiling algorithm (BoW, cosine similarity, depth scores, thresholding, segment boundaries).
- `segmenter_service.py`: Orchestrates the segmentation process by applying Sliding TextTiling and producing segment boundaries.
