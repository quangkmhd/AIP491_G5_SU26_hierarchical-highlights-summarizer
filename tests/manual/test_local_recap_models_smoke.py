"""Opt-in smoke test for both real local CUDA recap models."""

import pytest
import torch

from src.repo.model_loader import ModelLoader
from src.repo.seq2seq_inference import BARTphoTopicTitler, ViT5ChunkSummarizer


@pytest.mark.real_model
def test_local_recap_models_generate_on_cuda() -> None:
    assert torch.cuda.is_available(), "CUDA is required for the local recap model smoke test"
    loader = ModelLoader()
    summarizer = ViT5ChunkSummarizer(loader.load_chunk_summarizer())
    titler = BARTphoTopicTitler(loader.load_topic_titler())
    summary = summarizer.summarize(
        "Lan: Nhóm thống nhất hoàn thiện API trước thứ Sáu.\n"
        "Minh: Minh sẽ phụ trách kiểm thử tích hợp."
    )
    title = titler.generate_title(summary)
    assert summary.strip()
    assert title.strip()
