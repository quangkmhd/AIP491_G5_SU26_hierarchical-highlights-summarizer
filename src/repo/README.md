# Repository Layer

This directory acts as the data access and model storage layer.

## Role
- Handles loading machine learning models and weights (e.g., loading CoherenceNet and Hugging Face BERT models).
- Handles reading and parsing inputs from external files (e.g., reading JSON/TXT transcripts).
- Abstracts physical data sources from the core business logic.

## Rules
- **Dependency Limit**: Can only import from `types` and `config` layers.
- MUST NOT import from `service` or `runtime` layers.
- Should return clean domain objects defined in the `types` layer.

## Core Modules to Implement
- `coherence_net.py`: PyTorch Module architecture for coherence scoring.
- `model_loader.py`: Handles model initialization, loading checkpoints, and moving parameters to the appropriate device (CPU/GPU).
- `transcript_repo.py`: Reads raw transcript files and parses them into domain objects.
