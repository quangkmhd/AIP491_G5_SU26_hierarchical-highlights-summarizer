"""Manual smoke test for the real DeepFilterNet adapter."""

from __future__ import annotations

import numpy as np
import pytest

from src.service.audio_preprocessor import DeepFilterNetEnhancer


@pytest.mark.real_model
def test_deepfilternet_returns_finite_duration_preserving_audio() -> None:
    enhancer = DeepFilterNetEnhancer(atten_lim_db=15.0, post_filter=False)
    source = np.zeros(16000, dtype=np.float32)

    output = enhancer.enhance(source)

    assert output.shape == source.shape
    assert output.dtype == np.float32
    assert np.isfinite(output).all()
