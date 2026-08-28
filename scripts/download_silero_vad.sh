#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_PATH="$PROJECT_ROOT/backend/sd-module/weights/silero_vad.onnx"
MODEL_URL="https://raw.githubusercontent.com/snakers4/silero-vad/867c2aa692646a1f1de3e94a15c9dd9f614c0acb/src/silero_vad/data/silero_vad.onnx"
EXPECTED_SHA256="1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"

mkdir -p "$(dirname "$MODEL_PATH")"
curl --fail --location --output "$MODEL_PATH" "$MODEL_URL"

ACTUAL_SHA256="$(sha256sum "$MODEL_PATH" | awk '{print $1}')"
if [[ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]]; then
    echo "Silero VAD checksum mismatch at $MODEL_PATH" >&2
    exit 1
fi

echo "Silero VAD downloaded to backend/sd-module/weights/silero_vad.onnx"
