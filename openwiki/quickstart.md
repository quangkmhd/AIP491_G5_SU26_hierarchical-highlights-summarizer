# OpenWiki Quickstart

Welcome to the **LLM-Powered Hierarchical Meeting Recap System with Topic Segmentation** Wiki. This serves as the system-of-truth documentation designed for humans and future development agents.

This project delivers a streaming, unsupervised topic-segmentation and meeting-recap pipeline. Topic segmentation uses lexical Sliding TextTiling (BoW + cosine + multi-scale depth), while the presentation and user-experience follow guidelines from Paper 2 (hierarchical rolling chunk summaries + deferred titles).

---

## 🧭 Navigating the Wiki

```
openwiki/
├── quickstart.md             # This document (central navigation & overview)
├── architecture.md           # The strict 6-layer architecture and boundaries
├── workflows.md              # The 6-event end-to-end streaming and batch timelines
├── models_and_data.md        # Sliding TextTiling math, prompts, and schemas
└── operations.md             # Evaluation metrics, UX harnesses, CLI/Static API commands
```

Start with the core sections to understand how the system is put together:

*   **[System Architecture](architecture.md)**: Explore the strict directional model (`Types -> Config -> Repo -> Service -> Runtime -> UI`) and hard dependency enforcement.
*   **[Core Workflows](workflows.md)**: Understand the async streaming pipeline, how utterance streams yield events, and when rolling summaries & titles are calculated.
*   **[Models, Prompts & Data Validation](models_and_data.md)**: Deep dive into the Sliding TextTiling algorithm, Pydantic structural bounds, and prompt schemas.
*   **[System Operations & Testing](operations.md)**: Run the standard evaluation scripts, perform validation loops, use CLI diagnostic tools, and understand the test suite layout.

---

## 🚀 Rapid Onboarding & Bootstrap

This project is fully containerized and uses `uv` for lightning-fast Python dependency management.

### 1. Verification Path
To verify your environment is correctly bootstrapped and that all layers are in working order:

```bash
# Sync dependencies and build virtual environment
uv sync

# Run unified test suite (unit, integration, rules)
pytest tests/
```

### 2. Stand Up the Streaming Servers
The backend service serves both a REST API and a Server-Sent Events (SSE) streaming endpoint.

```bash
# Start the webapi and host the built-in streaming UI prototype
uv run uvicorn src.runtime.api:create_app --factory --port 8000
```
Open **`http://localhost:8000`** in your browser to view the interactive static frontend.

### 3. Run the CLI
The system provides a command-line interface supporting direct batch processing or NDJSON event emitting.

```bash
# Emet NDJSON events from standard or input files directly to stdout
uv run python -m src.runtime.cli stream data/eval_vi/meeting_committee.json

# Process and output a compact batch JSON summary to disk
uv run python -m src.runtime.cli process data/eval_vi/meeting_committee.json -o output.json
```

---

## 🛠 Working Contract for Agents

If you are an AI assistant or software agent making code modifications in this repository, you **must** strictly adhere to the following guardrails:

1.  **Do Not Violate Layer Boundaries**: The layer map is unidirectional. `src/types` must never import from config, repo, services, or runtime. This is mechanically checked on test runs via AST scanners.
2.  **No Extraneous Imports**: Centralize packages through standard libraries where possible. Do not import `time` or heavy wrappers in streaming modules where it is not used.
3.  **Local Execution Rules**: Runtime uses the CUDA-only checkpoints in `models/`; fast tests inject task doubles and never load weights or access the network.
4.  **Actionable Error Paths**: Never drop errors or silent OOM boundaries. When throwing exceptions or returning API failures, include the `fix` keyword pointing to a meaningful resolution. See **[Operations](operations.md)** for more details.
5.  **Clean Weight Storage**: The Vietnamese BERT weights are stored locally in the folder `vibert_checkpoints_vi/`. Never remove or rename this folder, and ensure it remains git-ignored.
