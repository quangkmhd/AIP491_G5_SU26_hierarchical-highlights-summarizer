# Detailed Implementation Plan - Backend Orchestration Layer & Containerized AI Pipeline

This document defines the implementation roadmap for building the **`backend/` Central Orchestration Layer**, setting up SQLite state persistence, exposing microservice APIs across isolated AI modules, and preparing for future `frontend/` UI integration and containerized deployment.

---

## 1. Microservice Architecture Topology

Each AI module operates in complete isolation with its own environment, model weights, dependencies, and configuration. The **`backend/`** module acts as the single central Gateway for the future `frontend/` UI.

```
                                  +---------------------------------------+
                                  |     Future Frontend UI (Later)        |
                                  +---------------------------------------+
                                                      │
                                                      │ HTTP / WebSockets
                                                      v
                                  +---------------------------------------+
                                  |      backend/ Orchestrator Gateway    |  (Port 8080)
                                  |   - Session Manager & State Machine   |
                                  |   - SQLite Database (schema.sql)      |
                                  |   - WebSocket Progress Broadcaster    |
                                  +---------------------------------------+
                                      │               │               │
            ┌─────────────────────────┘               │               └─────────────────────────┐
            │ REST / WS                               │ REST                                    │ REST
            v                                         v                                         v
+-----------------------+                 +-----------------------+                 +-----------------------+
|  sd-module Container  | (Port 8002)     |  asr-module Container | (Port 8001)     | llms-module Container | (Port 8000)
|  - Silero VAD         |                 |  - Sherpa-ONNX        |                 |  - Multiscale         |
|  - Conv-TasNet (BSS)  |                 |    Zipformer          |                 |    TextTiling         |
|  - SpeakerBeam (TSE)  |                 |  - Isolated Weights   |                 |  - ViT5 + BARTpho     |
|  - CAM++ Embedder     |                 |    (models/)          |                 |  - Isolated Weights   |
|  - Isolated Weights   |                 +-----------------------+                 |    (models/)          |
|    (weights/)         |                                                           +-----------------------+
+-----------------------+
```

---

## 2. Port Assignments & Environment Isolation

| Module / Service | Service Role | Port | Model Weights Directory | Internal Endpoint / API |
| :--- | :--- | :--- | :--- | :--- |
| **`backend/`** | Orchestrator & Gateway | **`8080`** | N/A (SQLite DB at `backend/db/pipeline.db`) | `POST /api/v1/sessions`<br>`WS /ws/sessions/{id}` |
| **`backend/sd-module/`** | Speaker Diarization | **`8002`** | `backend/sd-module/weights/` | `POST /api/v1/diarize`<br>`GET /healthz` |
| **`backend/asr-module/`** | Speech-to-Text | **`8001`** | `backend/asr-module/models/` | `POST /api/v1/transcribe`<br>`GET /healthz` |
| **`backend/llms-module/`** | Hierarchical Summarization | **`8000`** | `backend/llms-module/models/` | `POST /api/v1/meetings/process`<br>`GET /health` |

---

## 3. Database Schema & Data Persistence (`backend/db/`)

The SQLite database (`backend/db/pipeline.db`) manages session lifecycle, stores intermediate utterances, and saves final hierarchical summaries.

### Schema DDL (`backend/db/schema.sql`):

```sql
-- Session Metadata & Pipeline State Machine
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    audio_source TEXT,
    status TEXT CHECK(status IN ('created', 'diarizing', 'transcribing', 'summarizing', 'completed', 'failed')) DEFAULT 'created',
    progress_percentage REAL DEFAULT 0.0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transcribed Utterances
CREATE TABLE IF NOT EXISTS utterances (
    utterance_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    speaker_id TEXT NOT NULL,
    text TEXT NOT NULL,
    utterance_index INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    has_overlap INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Final LLM Summarization Output
CREATE TABLE IF NOT EXISTS summaries (
    summary_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    hierarchical_json TEXT NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_utterances_session ON utterances(session_id, utterance_index);
```

---

## 4. Pipeline Execution Flow & Async Routing

```
[Start Session] ──► [1. Diarize (sd-module)] ──► [2. Transcribe Async (asr-module)] ──► [3. Summarize (llms-module)] ──► [Complete]
```

### 1. Diarization Phase (`sd-module` Integration)
- Audio files or 500ms audio stream chunks are sent to `sd-module`.
- `sd-module` performs Silero VAD, Pyannote OVD, CAM++ voiceprint matching, and Conv-TasNet/SpeakerBeam separation for overlapping speech.
- Returns `speakers`, `audio_streams` (NumPy arrays), and `has_overlap` flag.

### 2. Async ASR Routing Phase (`asr-module` Integration)
- Converts NumPy arrays in-memory to `.wav` byte buffers without disk I/O.
- **Single Speaker (`has_overlap == False`)**: Sends 1 async HTTP POST request to `asr-module` (`http://localhost:8001/api/v1/transcribe`).
- **Multiple Speakers / Overlap (`has_overlap == True`)**: Sends $N$ parallel async HTTP POST requests (`asyncio.gather`) to `asr-module` for each separated speaker stream.
- Persists transcribed utterances directly into the SQLite database table `utterances`.

### 3. Summarization Phase (`llms-module` Integration)
- Queries transcribed utterances from SQLite, formats them into `TranscriptIngestionRequest`, and calls `llms-module` (`http://localhost:8000/api/v1/meetings/process`).
- Receives complete `HierarchicalSummary` JSON (topics, chunk summaries, chapter titles) and saves it to SQLite table `summaries`.

---

## 5. File Structure to Implement

```
.
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── sessions.py         # Session REST endpoints (POST/GET)
│   │   └── ws.py               # Live WebSocket progress broadcaster
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py         # Async SQLite connection manager
│   │   └── schema.sql          # DDL tables & indexes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_router.py     # NumPy to WAV buffer & async STT router
│   │   └── pipeline_orchestrator.py # Master 3-stage pipeline driver
│   ├── Dockerfile              # Docker container script for backend
│   ├── main.py                 # FastAPI application entrypoint (Port 8080)
│   └── requirements.txt        # Backend standalone dependencies
├── sd-module/
│   ├── api.py                  # NEW: FastAPI wrapper (/api/v1/diarize, Port 8002)
│   ├── Dockerfile
│   └── requirements.txt
├── asr-module/
│   ├── Dockerfile
│   └── requirements.txt
├── llms-module/
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml          # Container orchestrator running all 4 services
└── docs/
    ├── integration-plan.md
    └── implementation-plan.md
```

---

## 6. Implementation Checklist

- [ ] **Step 1**: Create `backend/db/schema.sql` and `backend/db/database.py` with async SQLite connection helper.
- [ ] **Step 2**: Add FastAPI HTTP wrapper `sd-module/api.py` (`POST /api/v1/diarize` & `GET /healthz`) running on Port 8002.
- [ ] **Step 3**: Implement `backend/services/audio_router.py` for NumPy-to-WAV conversion and parallel async STT dispatch (`asyncio.gather`).
- [ ] **Step 4**: Implement `backend/services/pipeline_orchestrator.py` managing the pipeline state machine ($0\% \rightarrow 30\% \rightarrow 70\% \rightarrow 100\%$) and error recording.
- [ ] **Step 5**: Implement REST routes `backend/api/sessions.py` and WebSocket broadcaster `backend/api/ws.py`.
- [ ] **Step 6**: Create `backend/main.py` entrypoint serving on Port 8080.
- [ ] **Step 7**: Create `docker-compose.yml` to package and run `backend`, `sd-module`, `asr-module`, and `llms-module` as containerized microservices.

---

## 7. Verification & Testing

1. **Database Test**: Verify SQLite tables (`sessions`, `utterances`, `summaries`) initialize cleanly from `backend/db/schema.sql`.
2. **Isolation Test**: Start `sd-module` on port 8002, `asr-module` on port 8001, `llms-module` on port 8000, and `backend/` on port 8080.
3. **Pipeline Test**: Send `data/sample_transcript.json` or audio file to `POST http://localhost:8080/api/v1/sessions`, track progress percentage, and retrieve the final summary output via `GET /api/v1/sessions/{session_id}/summary`.
