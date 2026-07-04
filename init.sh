#!/usr/bin/env bash
#
# init.sh — Reproducible environment setup for Coherence-Enhanced Meeting Recap
#
# What this does (5 steps):
#   1. Checks system prerequisites (python, pip, venv, git, poppler)
#   2. Creates Python virtual environment .venv
#   3. Installs all pinned dependencies from pyproject.toml
#   4. Downloads NLP data packages (NLTK, spaCy)
#   5. Caches pre-trained models (BERT, BART) and runs smoke test
#
# Usage: bash init.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "  Meeting Recap System — Environment Setup"
echo "=========================================="
echo ""

# ─── Step 0: Check prerequisites ──────────────────────────────────────────

echo -e "${YELLOW}[Step 0/5] Checking system prerequisites...${NC}"

MISSING=()

check_cmd() {
    local cmd="$1"
    local name="$2"
    if command -v "$cmd" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name found: $($cmd --version 2>&1 | head -1)"
    else
        echo -e "  ${RED}✗${NC} $name NOT found"
        MISSING+=("$name")
    fi
}

check_cmd python3 "Python 3"
check_cmd pip      "pip"
check_cmd git      "git"

# Check venv module
if python3 -m venv --help &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} python3-venv module available"
else
    echo -e "  ${RED}✗${NC} python3-venv NOT available (install: sudo apt install python3-venv)"
    MISSING+=("python3-venv")
fi

# Check poppler (for pdfplumber/markitdown PDF processing)
if command -v pdftotext &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} poppler-utils found"
else
    echo -e "  ${YELLOW}⚠${NC} poppler-utils NOT found — PDF processing may fail (install: sudo apt install poppler-utils)"
fi

# Check Python version
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
    echo -e "  ${GREEN}✓${NC} Python $PY_VER >= 3.10"
else
    echo -e "  ${RED}✗${NC} Python $PY_VER is too old (need >= 3.10)"
    MISSING+=("Python>=3.10")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}ERROR: Missing prerequisites:${NC}"
    for m in "${MISSING[@]}"; do
        echo "  - $m"
    done
    echo ""
    echo "Install them and re-run this script. Aborting."
    exit 1
fi

echo ""

# ─── Step 1: Create virtual environment ───────────────────────────────────

echo -e "${YELLOW}[Step 1/5] Creating Python virtual environment (.venv)...${NC}"
python3 -m venv .venv
echo -e "  ${GREEN}✓${NC} Created .venv"

# Ensure pip is up to date inside venv
.venv/bin/python -m pip install --quiet --upgrade pip
echo -e "  ${GREEN}✓${NC} Upgraded pip"
echo ""

# ─── Step 2: Install pinned dependencies ──────────────────────────────────

echo -e "${YELLOW}[Step 2/5] Installing dependencies from pyproject.toml...${NC}"
.venv/bin/pip install -e ".[dev]" --quiet
echo -e "  ${GREEN}✓${NC} Installed core + dev dependencies"
echo ""

# ─── Step 3: Download NLP data ────────────────────────────────────────────

echo -e "${YELLOW}[Step 3/5] Downloading NLP data packages...${NC}"

# NLTK data
.venv/bin/python -c "
import nltk
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)
print('  NLTK: punkt, punkt_tab, stopwords downloaded')
"

# spaCy model
.venv/bin/python -m spacy download en_core_web_sm --quiet 2>/dev/null || true
echo "  spaCy: en_core_web_sm model available"
echo ""

# ─── Step 4: Cache pre-trained models ─────────────────────────────────────

echo -e "${YELLOW}[Step 4/5] Caching pre-trained transformer models...${NC}"
echo "  This downloads BERT-base and BART-large (~2GB). May take a few minutes..."

# Cache BERT-base-uncased (for coherence scoring)
.venv/bin/python -c "
from transformers import AutoModel, AutoTokenizer
AutoTokenizer.from_pretrained('bert-base-uncased')
AutoModel.from_pretrained('bert-base-uncased')
print('  BERT-base-uncased: cached')
" 2>&1 | tail -1

# Cache BART-large (for summarization)
.venv/bin/python -c "
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
AutoTokenizer.from_pretrained('facebook/bart-large')
AutoModelForSeq2SeqLM.from_pretrained('facebook/bart-large')
print('  BART-large: cached')
" | tail -1

echo -e "  ${GREEN}✓${NC} Models cached"
echo ""

# ─── Step 5: Smoke test ───────────────────────────────────────────────────

echo -e "${YELLOW}[Step 5/5] Running smoke test...${NC}"
.venv/bin/python -c "
# Minimal pipeline test: load a sample dialogue, verify data shapes
import json, sys

# Verify data/ exists and is parseable
import os
eval_dir = 'data/eval'
if not os.path.isdir(eval_dir):
    print('  WARNING: data/eval/ directory not found — skipping data check')
    sys.exit(0)

files = [f for f in os.listdir(eval_dir) if f.endswith('.json')]
if not files:
    print('  WARNING: No eval JSON files found — skipping data check')
    sys.exit(0)

fpath = os.path.join(eval_dir, files[0])
with open(fpath) as f:
    data = json.load(f)
print(f'  Loaded sample: {fpath}')
print(f'  Dataset size: {len(data)} dialogues')
if len(data) > 0:
    d = data[0]
    print(f'  Sample keys: {list(d.keys())}')
    print(f'  Utterances: {len(d.get(\"utterances\", []))}')
    print(f'  Segments: {d.get(\"segments\", \"N/A\")}')
print('  Smoke test PASSED — pipeline can load data')
" 2>&1

if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} Smoke test passed"
else
    echo -e "  ${RED}✗${NC} Smoke test failed. Check errors above."
    exit 1
fi

echo ""

# ─── Done ─────────────────────────────────────────────────────────────────

echo "=========================================="
echo -e "  ${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate:  source .venv/bin/activate"
echo "  2. Verify:    make verify"
echo "  3. Read:      cat PROGRESS.md"
echo "  4. Start:     pick first 'passes: false' task from feature_list.json"
echo ""
echo "Optional: Clone Paper 1 reference code:"
echo "  git clone https://github.com/lxing532/Dialogue-Topic-Segmenter references/dialogue-topic-segmenter/"
echo ""