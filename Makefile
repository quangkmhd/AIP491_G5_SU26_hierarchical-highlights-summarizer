.PHONY: help init install lint format typecheck test test-e2e verify clean train-coherence segment recap evaluate paper-figs

# Default target: show all available commands
help:
	@echo "Coherence-Enhanced Meeting Recap — Available Commands"
	@echo "======================================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install all dependencies (requires .venv)"
	@echo "  make init           Full init: create .venv + install + download models"
	@echo ""
	@echo "Verification (must pass before commit):"
	@echo "  make lint           Run ruff linter"
	@echo "  make format         Auto-format code with ruff"
	@echo "  make typecheck      Run mypy static type checking"
	@echo "  make test           Run pytest unit tests"
	@echo "  make test-e2e       Run end-to-end pipeline test"
	@echo "  make verify         Full check: lint → typecheck → test"
	@echo ""
	@echo "Pipeline:"
	@echo "  make train-coherence  Train utterance-pair coherence model"
	@echo "  make segment          Run topic segmentation on eval datasets"
	@echo "  make recap            Generate meeting recaps"
	@echo "  make evaluate         Compute Pk, WinDiff, F1 metrics"
	@echo ""
	@echo "Paper:"
	@echo "  make paper-figs       Generate figures and tables for paper"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove __pycache__, .mypy_cache, outputs/*"
	@echo ""

# ─── Setup ────────────────────────────────────────────────────────────────

init:
	@echo "==> Running init.sh for full environment setup..."
	bash init.sh

install:
	@echo "==> Installing dependencies..."
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/python -m spacy download en_core_web_sm
	@echo "==> Done. Run 'make verify' to confirm everything works."

# ─── Verification (Feedback layer — highest ROI) ──────────────────────────

lint:
	.venv/bin/ruff check src/ tests/

format:
	.venv/bin/ruff format src/ tests/
	.venv/bin/ruff check --fix src/ tests/

typecheck:
	.venv/bin/mypy src/

test:
	.venv/bin/pytest -x --cov=src/ --cov-report=term-missing

test-e2e:
	.venv/bin/pytest tests/e2e/ -v -m integration

verify: lint typecheck test
	@echo ""
	@echo "========================================"
	@echo "  All checks passed — ready to commit"
	@echo "========================================"

# ─── Pipeline ─────────────────────────────────────────────────────────────

train-coherence:
	.venv/bin/python -m src.coherence.train

segment:
	.venv/bin/python -m src.segmentation.run

recap:
	.venv/bin/python -m src.summarization.run

evaluate:
	.venv/bin/python -m src.evaluation.run

paper-figs:
	.venv/bin/python -m src.evaluation.generate_figures

# ─── Maintenance ──────────────────────────────────────────────────────────

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf outputs/* 2>/dev/null || true
	@echo "==> Clean."