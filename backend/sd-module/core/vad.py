"""Core VAD — Silero VAD Adapter (ONNX, Offline)."""

import logging
import os
import numpy as np
import torch
from config.paths import get_full_path, to_relative_path
from utils.silero_vad_utils import OnnxWrapper, get_speech_timestamps

logger = logging.getLogger(__name__)


class SileroVAD:
    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)

        model_path = config.get("model_paths", {}).get("silero_vad_onnx", "weights/silero_vad.onnx")
        model_path = get_full_path(model_path)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Silero VAD ONNX model not found at: {model_path}")

        rel_path = to_relative_path(model_path)
        logger.info(f"[VAD] Loading Silero VAD ONNX model from: '{rel_path}'...")
        self.model = OnnxWrapper(model_path, force_onnx_cpu=True)
        logger.info(f"[VAD] Silero VAD initialized successfully (Sample Rate: {self.sr}Hz).")

    def process(self, clean_audio_chunk: np.ndarray) -> tuple[float, float]:
        """Analyze clean audio chunk and return (speech_duration_sec, avg_confidence)."""
        audio_tensor = torch.from_numpy(clean_audio_chunk).float()

        probs = self.model.audio_forward(audio_tensor, self.sr)

        t_c = 0.0
        t_d = 0.0
        if probs is not None and probs.numel() > 0:
            t_c = probs.mean().item()
            active_frames = (probs > 0.5).sum().item()
            hop_length = 512
            t_d = active_frames * (hop_length / self.sr)

        return t_d, t_c
