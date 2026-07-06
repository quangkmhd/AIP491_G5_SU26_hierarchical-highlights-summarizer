#!/usr/bin/env bash
set -euo pipefail

# Download model artifacts needed by the meeting-recap pipeline.
# Runs from repo root. Idempotent — skips files that already exist.
#
# Models:
#   1. NSP base model + tokenizer: FPTAI/vibert-base-cased (HF cache)
#   2. NSP checkpoint: already in-repo at vibert_checkpoints_vi/cpt_4000.pth
#   3. LLM backbone: unsloth/gemma-4-E2B-it-qat-GGUF (GGUF, via HF)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Downloading models for meeting-recap ==="

# 1. NSP base model + tokenizer — cached by transformers
echo "[1/2] Caching NSP base model + tokenizer (FPTAI/vibert-base-cased)..."
uv run python -c "
from transformers import AutoModel, AutoTokenizer
AutoModel.from_pretrained('FPTAI/vibert-base-cased')
AutoTokenizer.from_pretrained('FPTAI/vibert-base-cased')
print('base model + tokenizer cached OK')
"

# 2. LLM backbone GGUF
echo "[2/2] Downloading LLM backbone GGUF (gemma-4-E2B-it-qat)..."
uv run python -c "
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id='unsloth/gemma-4-E2B-it-qat-GGUF',
    filename='gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf',
)
print(f'GGUF downloaded to: {path}')
"

echo "=== All models ready ==="
