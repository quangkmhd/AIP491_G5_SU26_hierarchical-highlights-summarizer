#!/usr/bin/env bash
set -euo pipefail

# Provision inference-only artifacts from the adjacent training project.
# Despite the historical filename, this script performs no network download.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${ROOT}/../16-dts-tsl/models"

mkdir -p "${ROOT}/models/vit5-chunk-summarizer-v1"
mkdir -p "${ROOT}/models/bartpho-topic-titler-v2"

cp "${SOURCE}/vit5-chunk-summarizer-v1/"{config.json,generation_config.json,model.safetensors,tokenizer.json,tokenizer_config.json} \
  "${ROOT}/models/vit5-chunk-summarizer-v1/"

TITLE_SOURCE="${SOURCE}/bartpho-topic-titler-v2/checkpoint-184"
cp "${TITLE_SOURCE}/"{config.json,generation_config.json,model.safetensors,dict.txt,sentencepiece.bpe.model,tokenizer_config.json} \
  "${ROOT}/models/bartpho-topic-titler-v2/"

echo "Local ViT5 and BARTpho inference artifacts provisioned under ${ROOT}/models"
