# Hierarchical Highlights Summarizer & Meeting Pipeline

An end-to-end, multi-stage AI meeting intelligence system featuring:
1. **Target Speaker Diarization (`backend/sd-module`)**: Silero VAD + Pyannote OVD + CAM++ Voiceprint Embedder + Conv-TasNet (BSS) & SpeakerBeam (TSE) voice separation.
2. **Speech-to-Text Microservice (`backend/asr-module`)**: Sherpa-ONNX Zipformer Transducer engine.
3. **LLM Summarization Engine (`backend/llms-module`)**: Multiscale TextTiling topic segmentation + ViT5 chunk summarizer + BARTpho topic titler.
4. **Central Orchestrator Gateway (`backend/`)**: FastAPI + SQLite state machine + WebSocket streaming engine (Port `8080`).

---

## Service Port Assignments

| Service | Directory | Port | Primary Endpoint |
| :--- | :--- | :--- | :--- |
| **Backend Gateway** | `backend/` | **`8080`** | `POST http://localhost:8080/api/v1/sessions` |
| **Speaker Diarization** | `backend/sd-module/` | **`8002`** | `POST http://localhost:8002/api/v1/diarize` |
| **Speech-to-Text ASR** | `backend/asr-module/` | **`8001`** | `POST http://localhost:8001/api/v1/transcribe` |
| **LLM Summarization** | `backend/llms-module/` | **`8000`** | `POST http://localhost:8000/api/v1/meetings/process` |

---

## Method 1: Run with Docker Compose (Recommended)

To build and run all 4 isolated microservice containers automatically:

```bash
docker-compose up --build
```

---

## Method 3: Launch Pure-Python Streamlit UI (`frontend/`)

Create a local virtualenv inside `frontend/` and run the Streamlit web demo:

```bash
# 1. Create virtual environment inside frontend directory
python -m venv frontend/venv

# 2. Install frontend dependencies
./frontend/venv/bin/pip install -r frontend/requirements.txt

# 3. Launch Streamlit UI
./frontend/venv/bin/streamlit run frontend/app.py
```

Access the pure-Python web interface in your browser at `http://localhost:8501`.

### Step 1: Install Dependencies

Ensure Python 3.11+ is installed, then install the root requirements:

```bash
pip install -r backend/requirements.txt
```

### Step 2: Download Model Weights (Manual Download Guide)

Ensure model weights are placed in their respective directories:
- **`backend/sd-module/weights/`**: Model weights for Silero VAD, DeepFilterNet3, Pyannote OVD, CAM++, Conv-TasNet, and SpeakerBeam.
- **`backend/asr-module/models/`**: Sherpa-ONNX Zipformer models (`encoder-epoch-99-avg-1.onnx`, `decoder-epoch-99-avg-1.onnx`, `joiner-epoch-99-avg-1.onnx`, `tokens.txt`).
- **`backend/llms-module/models/`**: ViT5 and BARTpho pre-trained weights.

---

### Step 3: Launch Microservices in Terminal Windows

Open **4 terminal windows** to run each service independently:

#### Terminal 1: LLM Summarization Service (Port 8000)
```bash
PYTHONPATH=backend/llms-module uvicorn backend.llms-module.runtime.api:create_app --factory --host 0.0.0.0 --port 8000
```

#### Terminal 2: Speech-to-Text ASR Service (Port 8001)
```bash
PYTHONPATH=backend/asr-module uvicorn backend.asr-module.main:app --host 0.0.0.0 --port 8001
```

#### Terminal 3: Speaker Diarization Service (Port 8002)
```bash
PYTHONPATH=backend/sd-module uvicorn backend.sd-module.api:create_app --factory --host 0.0.0.0 --port 8002
```

#### Terminal 4: Central Backend Gateway (Port 8080)
```bash
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
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
