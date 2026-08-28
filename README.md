# Hierarchical Highlights Summarizer & Meeting Intelligence System

An end-to-end, multi-stage AI meeting intelligence and transcription system featuring:
1. **Target Speaker Diarization (`backend/sd-module`)**: Silero VAD + Pyannote OVD + CAM++ Voiceprint Embedder + Conv-TasNet (BSS) & SpeakerBeam (TSE) voice separation.
2. **Speech-to-Text Microservice (`backend/asr-module`)**: Sherpa-ONNX Zipformer Transducer engine.
3. **LLM Summarization Engine (`backend/llms-module`)**: Multiscale TextTiling topic segmentation + ViT5 chunk summarizer + BARTpho topic titler.
4. **Central Orchestrator Gateway (`backend/`)**: FastAPI + SQLite state machine + WebSocket streaming engine (Port `8080`).
5. **Modern Web Frontend (`frontend/`)**: React + Vite interface for real-time and batch audio processing (Port `8501`).

---

## Service Port Assignments

| Service | Directory | Port | Primary Endpoint | Swagger Docs |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Gateway** | `backend/` | **`8080`** | `POST http://localhost:8080/api/v1/sessions` | `http://localhost:8080/docs` |
| **ASR (Speech-to-Text)** | `backend/asr-module/` | **`8000`** | `POST http://localhost:8000/api/v1/transcribe` | `http://localhost:8000/docs` |
| **Speaker Diarization** | `backend/sd-module/` | **`8002`** | `POST http://localhost:8002/api/v1/diarize` | `http://localhost:8002/docs` |
| **LLM Summarization** | `backend/llms-module/` | **`8003`** | `POST http://localhost:8003/api/v1/meetings/process` | `http://localhost:8003/docs` |
| **Frontend UI** | `frontend/` | **`8501`** | `http://localhost:8501` | — |

---

## Prerequisites & Model Weights

### 1. Python & Node.js Requirements
- Python 3.11+
- Node.js 18+ and npm
- `virtualenv` (`pip install virtualenv`)

### 2. Download Model Weights
Ensure model weights are placed in their respective submodule directories:
- **`backend/sd-module/weights/`**: Model weights for Silero VAD, DeepFilterNet3, Pyannote OVD, CAM++, Conv-TasNet, and SpeakerBeam.
- **`backend/asr-module/models/`**: Sherpa-ONNX Zipformer models (`encoder.onnx`, `decoder.onnx`, `joiner.onnx`, `tokens.txt`).
- **`backend/llms-module/models/`**: ViT5 and BARTpho pre-trained weights.

Download the compatible Silero VAD checkpoint without changing its configured name or location:

```bash
bash scripts/download_silero_vad.sh
```

---

## Local Setup & Installation

Each microservice uses its own dedicated virtual environment to maintain isolated dependency trees without version conflicts.

```bash
# 1. ASR Module
cd backend/asr-module
virtualenv .asr-module-venv
source .asr-module-venv/bin/activate
pip install -r asr-module-requirements.txt
deactivate && cd ../..

# 2. SD Module
cd backend/sd-module
virtualenv .sd-module-venv
source .sd-module-venv/bin/activate
pip install -r sd-module-requirements.txt
deactivate && cd ../..

# 3. LLMs Module
cd backend/llms-module
virtualenv .llms-module-venv
source .llms-module-venv/bin/activate
pip install -r llms-module-requirements.txt
deactivate && cd ../..

# 4. Central Backend Gateway
cd backend
virtualenv .backend-gateway-venv
source .backend-gateway-venv/bin/activate
pip install -r requirements.txt
deactivate && cd ..

# 5. Frontend UI
cd frontend
npm install
cd ..
```

---

## Running the System

### Method 1: Unified Local Script (Recommended)

Run all microservices and the frontend with a single command:

**macOS / Linux:**
```bash
bash scripts/start_local.sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1
```

---

### Method 2: Launch Microservices Individually

You can also run each service in a separate terminal:

#### Terminal 1: ASR Service (Port 8000)
```bash
cd backend/asr-module
PYTHONPATH=. .asr-module-venv/bin/python main.py
```

#### Terminal 2: Speaker Diarization Service (Port 8002)
```bash
cd backend/sd-module
PYTHONPATH=. .sd-module-venv/bin/python -m uvicorn api:create_app --factory --host 0.0.0.0 --port 8002
```

#### Terminal 3: LLM Summarization Service (Port 8003)
```bash
cd backend/llms-module
PYTHONPATH=. .llms-module-venv/bin/python -m uvicorn runtime.api:create_app --factory --host 0.0.0.0 --port 8003
```

#### Terminal 4: Central Backend Gateway (Port 8080)
```bash
PYTHONPATH=. backend/.backend-gateway-venv/bin/python -m uvicorn backend.main:create_app --factory --host 0.0.0.0 --port 8080 --reload --reload-dir backend
```

#### Terminal 5: React Frontend (Port 8501)
```bash
cd frontend
npm run dev -- --port 8501 --host
```

---

### Method 3: Docker Compose

To build and run all containerized microservices:

```bash
docker-compose up --build
```

---

## Testing & Interacting with the API

### 1. Check Gateway Health
```bash
curl http://localhost:8080/health
```

### 2. Process an Audio File (Batch Upload)
```bash
curl -X POST http://localhost:8080/api/v1/sessions \
  -F "title=Weekly Engineering Sync" \
  -F "file=@sample_audio.wav"
```

### 3. Check Session Progress & Transcribed Utterances
```bash
curl http://localhost:8080/api/v1/sessions/{session_id}
```

### 4. Fetch Final Hierarchical Summary Output
```bash
curl http://localhost:8080/api/v1/sessions/{session_id}/summary
```

### 5. WebSocket Real-Time Audio Streaming
Connect your client / microphone stream to:
```text
ws://localhost:8080/ws/sessions/{session_id}/stream
```
Stream binary PCM 16kHz audio frames (500ms chunks) to receive live `utterance-emitted` and `progress-updated` events.

Each ASR utterance is persisted and forwarded immediately to a dedicated LLM
WebSocket for that meeting. TextTiling owns its 40-utterance analysis window;
the Gateway doesn't batch utterances. Finish a REST-created live meeting with:

```bash
curl -X POST http://localhost:8080/api/v1/sessions/{session_id}/finalize
```

Finalization rejects later audio, flushes trailing diarization/ASR output, then
flushes the topic segmenter and stores the authoritative summary.
