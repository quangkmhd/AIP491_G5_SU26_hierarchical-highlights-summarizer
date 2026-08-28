from pathlib import Path

import torch

from utils.silero_vad_utils import OnnxWrapper


def test_wrapper_runs_downloaded_checkpoint_at_stable_model_path() -> None:
    model_path = Path(__file__).resolve().parents[1] / "weights" / "silero_vad.onnx"
    wrapper = OnnxWrapper(str(model_path), force_onnx_cpu=True)

    probabilities = wrapper.audio_forward(torch.zeros(1, 16000), 16000)

    assert probabilities.shape == (1, 32)
    assert torch.isfinite(probabilities).all()
