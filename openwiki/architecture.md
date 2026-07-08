# 🏛 System Architecture

This project is built from the ground up using a strict, multi-tier directional architectural design. Layers are decoupled, easily testable, and have strict, mechanically enforced boundary rules.

---

## 🗺 The 6-Layer Architecture

We organize our codebase vertically as follows:

$$\text{Types} \rightarrow \text{Config} \rightarrow \text{Repo} \rightarrow \text{Service} \rightarrow \text{Runtime} \rightarrow \text{UI}$$

### Detailed Layer Maps

| Layer | Path | Purpose / Responsibilities | Key Rules & Constraints |
| :--- | :--- | :--- | :--- |
| **Types** | `src/types/` | Data containers, structures, schemas, and basic structural invariants. | **Forbidden from importing from any other layer.** Immutable data types (e.g., `Utterance`, `DialogueTranscript`). |
| **Config** | `src/config/` | System configuration definitions, environment variable parsers, and defaults. | Can import `types`, but **cannot import `repo`, `service`, `runtime`, or `ui`**. Powered by Pydantic settings. |
| **Repo**| `src/repo/` | Input/output adapters, persistence triggers, ML weight handlers, model loaders. | Direct data interaction only (filesystem, HF hub, or local checkpoints). Must not host high-level orchestrator logic. |
| **Service**| `src/service/` | Core business logic, mathematical text tiling, chunkers, and streaming engines. | Contains all algorithm implementations. Coordinates repos and config items into a cohesive unit. |
| **Runtime**| `src/runtime/` | Communication interfaces: CLI structures, Web server endpoints, middleware. | Acts as the shell interface surrounding the service modules. Instantiates services lazily. |
| **UI** | `src/ui/` | Client-side visual representation. Static index files and vanilla JS. | Communicates exclusively with the runtime API layer via REST or SSE streams. |

---

## 🧱 Dependency Enforcement Guidelines

To ensure the repository maintains its modularity and prevents spaghetti dependency strings:

1.  **Lower layers must never depend on higher layers**: This rule is checked via AST code-scans embedded in the unit tests (e.g., `tests/unit/test_repo_layer_rules.py`). 
2.  **No direct UI bypass**: The UI cannot access database, local file resources, or model singletons without entering through standard HTTP endpoints.
3.  **No import of cross-cutting wrappers**: Avoid circular dependency networks by restricting standard logging helpers (`src/logging.py`) and standard JSON interfaces from referencing specific service singletons.

---

## 🗺 Service & File Directory Map

Here is the architectural entry point mapping for the core components:

```
src/
├── types/
│   ├── utterance.py             # Utterance container (frozen representation)
│   ├── transcript.py            # Contiguous full dialogue transcript structure
│   └── hierarchical_recap.py    # Structured output schema (Chapters, Chunks, Metadata)
├── config/
│   ├── language.py              # BCP-47 tag mapping ("vi" and "FPTAI/vibert-base-cased")
│   └── text_tiling.py           # Window size, slide, and alpha parameters
├── repo/
│   ├── model_loader.py          # Process singleton model caching
│   ├── coherence_net.py         # The PyTorch BERT neural net architecture definition
│   └── prompts_vi.py            # Centralized Vietnamese YAML/JSON task prompt string constants
└── service/
    ├── coherence_scorer.py      # Computes pair scores between sequential utterance pairs
    ├── text_tiling.py           # Executes Hearst 1997 valley analysis
    ├── chunking_service.py      # Splits segment dialogues into <= 8 utterance chunks
    ├── hierarchical_summarization.py # Hits the backbone for rolling summaries and chapter titles
    └── meeting_recap_orchestrator.py # Wires the whole streaming flow together (the orchestrator)
```
