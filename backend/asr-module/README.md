# ASR Standalone Hosting Module (`asr-module`)

This is a self-contained, portable speech-to-text (ASR) microservice for Vietnamese, built on **Sherpa-ONNX** and **FastAPI**.

All neural network models, tokenizers, code, configuration, logging, and container setup are packaged entirely within this single `asr-module/` directory deploy it immediately.

---

## Directory Structure

```
asr-module/
├── config/                  # Configuration & Environment settings
│   ├── __init__.py
│   └── settings.py          # Pydantic Settings class
├── domain/                  # Domain entities & interfaces (Business Core)
│   ├── __init__.py
│   ├── entities.py          # AudioSegment & TranscriptionResult dataclasses
│   └── interfaces.py        # ASRModelInterface definition
├── infrastructure/          # External drivers & I/O adapters
│   ├── __init__.py
│   ├── logger.py            # Structured logging configuration
│   ├── audio_processor.py   # Audio loading & 16kHz resampling helper
│   └── sherpa_onnx_driver.py# Sherpa-ONNX model engine implementation
├── application/             # Application Use Cases
│   ├── __init__.py
│   └── transcribe_service.py# TranscribeAudioUseCase logic
├── presentation/            # API Controllers & Schemas (HTTP Layer)
│   ├── __init__.py
│   ├── api_v1.py            # FastAPI Router (/api/v1/transcribe, /healthz, /readyz)
│   └── schemas.py           # Pydantic Request/Response DTOs
├── models/                  # ONNX Model Artifacts (Downloaded manually from Google Drive)
│   ├── encoder.onnx         # Acoustic Zipformer Encoder
│   ├── decoder.onnx         # Predictor / Decoder Model
│   ├── joiner.onnx          # Transducer Joiner Model
│   └── tokens.txt           # BPE 2000 Vocabulary mapping
├── main.py                  # Server entrypoint & dependency injection
├── requirements.txt         # Standalone Python dependencies
├── .env.example             # Template for environment variables
├── Dockerfile               # Production Docker container definition
├── docker-compose.yml       # One-command Docker deployment setup
└── README.md                # Deployment and usage documentation
```

---

## 1. Portability

To host this service on another computer:

1. Compress the entire `asr-module/` folder into an archive:
   ```bash
   tar -czvf asr-module.tar.gz asr-module/
   # OR: zip -r asr-module.zip asr-module/
   ```
2. Copy `asr-module.tar.gz` (or `asr-module.zip`) to the target machine via `scp`, USB drive, or cloud storage.
3. Unpack it on the target machine:
   ```bash
   tar -xzvf asr-module.tar.gz
   cd asr-module
   ```

No extra model downloading or code dependency from outer folders is required!

---

## 2. How to Run

### Option A: Running with Docker Compose (Recommended)

Requires [Docker](https://docs.docker.com/get-docker/) & Docker Compose.

```bash
cd asr-module

# Build image and start service in detached mode
docker-compose up --build -d

# View live application logs
docker-compose logs -f
```

The service will be listening at `http://0.0.0.0:8000`.

To stop the service:
```bash
docker-compose down
```

---

### Option B: Running Standalone with Python

Requires Python

1. Create a virtual environment & install dependencies:
   ```bash
   cd asr-module
   python3 -m venv .asr-module-venv
   source .asr-module-venv/bin/activate
   pip install -r asr-module-requirements.txt
   ```

2. Start the service:
   ```bash
   python main.py
   ```

---

## 3. API Endpoints

Interactive Swagger API docs will be available at: `http://localhost:8000/docs`

### A. Health & Readiness

* **Liveness**:
  ```bash
  curl http://localhost:8000/healthz | python -m json.tool --no-ensure-ascii
  ```
  *Response:* `{"status":"alive","app":"ASR Hosting Service","version":"1.0.0"}`

* **Readiness**:
  ```bash
  curl http://localhost:8000/readyz | python -m json.tool --no-ensure-ascii
  ```
  *Response:* `{"status":"ready","app":"Hosting Service","version":"1.0.0"}`

### B. Transcribe Audio File

**Endpoint**: `POST /api/v1/transcribe`  
**Content-Type**: `multipart/form-data`  
**Accepted Audio Formats**: `.wav`, `.mp3`, `.flac` (auto-converted/resampled to 16kHz mono).

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -F "file=@data/audio-sample.wav" | python -m json.tool --no-ensure-ascii
```

**Response Format**:
```json
{
  "filename": "audio_sample.wav",
  "text": "xin chào đây là mô hình nhận dạng tiếng việt",
  "duration_seconds": 3.45,
  "sample_rate": 16000,
  "status": "success"
}
```

---

## 4. Environment Variables

Customize the service by creating a `.env` file or passing environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `HOST` | `0.0.0.0` | Host IP binding |
| `PORT` | `8000` | Port number |
| `NUM_THREADS` | `4` | Number of CPU threads for ONNX inference |
| `DECODING_METHOD` | `greedy_search` | `greedy_search` or `modified_beam_search` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MODEL_ENCODER_PATH` | `models/encoder.onnx` | Path to ONNX Encoder model |
| `MODEL_DECODER_PATH` | `models/decoder.onnx` | Path to ONNX Decoder model |
| `MODEL_JOINER_PATH` | `models/joiner.onnx` | Path to ONNX Joiner model |
| `TOKENS_PATH` | `models/tokens.txt` | Path to tokens vocabulary |
