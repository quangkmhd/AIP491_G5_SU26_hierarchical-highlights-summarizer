#!/usr/bin/env bash
# ==============================================================================
# Unified Local System Launcher Script
# Hierarchical Highlights Summarizer System
#
# Automatically targets dedicated virtual environments:
#   1. ASR-Module (Port 8000)   -> .asr-module-venv/bin/python
#   2. SD-Module  (Port 8002)   -> .sd-module-venv/bin/python
#   3. LLMs-Module(Port 8003)   -> .llms-module-venv/bin/python
#   4. Backend Gateway (8080)   -> .sd-module-venv/bin/python (PYTHONPATH=.)
#   5. Frontend   (Port 8501)   -> frontend/venv/bin/streamlit
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "LAUNCHING HIERARCHICAL HIGHLIGHTS SUMMARIZER SYSTEM (LOCAL MODE)"
echo "======================================================================"

# Signal Handler to gracefully terminate all background microservice processes
cleanup() {
    echo ""
    echo "======================================================================"
    echo "STOPPING ALL LOCAL MICROSERVICES..."
    echo "======================================================================"
    kill $(jobs -p) 2>/dev/null || true
    echo "All microservice processes stopped cleanly."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start ASR-Module (Port 8000)
echo "[1/5] Starting ASR-Module (Sherpa-ONNX) on http://localhost:8000 ..."
cd "$PROJECT_ROOT/backend/asr-module"
PYTHONPATH=. "$PROJECT_ROOT/backend/asr-module/.asr-module-venv/bin/python" main.py &

# 2. Start SD-Module (Port 8002)
echo "[2/5] Starting SD-Module (Diarization) on http://localhost:8002 ..."
cd "$PROJECT_ROOT/backend/sd-module"
PYTHONPATH=. "$PROJECT_ROOT/backend/sd-module/.sd-module-venv/bin/python" -m uvicorn api:create_app --factory --host 0.0.0.0 --port 8002 &

# 3. Start LLMs-Module (Port 8003)
echo "[3/5] Starting LLMs-Module (ViT5 / BARTpho) on http://localhost:8003 ..."
cd "$PROJECT_ROOT/backend/llms-module"
PYTHONPATH=. "$PROJECT_ROOT/backend/llms-module/.llms-module-venv/bin/python" -m uvicorn runtime.api:create_app --factory --host 0.0.0.0 --port 8003 &

# 4. Start Central Backend Gateway (Port 8080)
echo "[4/5] Starting Central Backend Gateway on http://localhost:8080 ..."
cd "$PROJECT_ROOT"
PYTHONPATH=. "$PROJECT_ROOT/backend/sd-module/.sd-module-venv/bin/python" -m uvicorn backend.main:create_app --factory --host 0.0.0.0 --port 8080 --reload &

# Wait for Backend Gateway (Port 8080) readiness before opening Frontend UI
echo "Waiting for Backend Gateway (Port 8080) readiness probe..."
for i in {1..20}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "Backend Gateway is online and ready!"
        break
    fi
    sleep 0.3
done

# 5. Start React Frontend UI (Port 8501)
if [ -d "$PROJECT_ROOT/frontend" ]; then
    echo "[5/5] Starting React Frontend Interface on http://localhost:8501 ..."
    cd "$PROJECT_ROOT/frontend"
    npm run dev -- --port 8501 --host &
fi

echo "======================================================================"
echo "ALL SYSTEM SERVICES LAUNCHED AND RUNNING!"
echo "   - ASR Service:      http://localhost:8000/docs"
echo "   - SD Service:       http://localhost:8002/docs"
echo "   - LLM Service:      http://localhost:8003/docs"
echo "   - Backend Gateway:  http://localhost:8080/docs"
echo "   - Frontend UI:      http://localhost:8501"
echo "======================================================================"
echo "Press Ctrl+C at any time to shutdown all microservices."

# Keep script active to await processes
wait
