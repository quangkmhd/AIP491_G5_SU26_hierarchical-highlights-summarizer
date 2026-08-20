"""
Core VAD \u2014 Silero VAD Adapter (ONNX, Offline)
Analyzes clean audio chunks, returns T_d (speech duration) and T_c (average confidence).
Uses OnnxWrapper + get_speech_timestamps from prepare/Silero/.
"""
import os
import sys
import torch
import numpy as np
import logging
from config.paths import get_full_path

logger = logging.getLogger(__name__)

# Import from utils
from utils.silero_vad_utils import OnnxWrapper, get_speech_timestamps


class SileroVAD:
    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)

        # Path to local ONNX file
        model_path = config.get("model_paths", {}).get("silero_vad_onnx", "weights/silero_vad.onnx")
        model_path = get_full_path(model_path)
        
        utils_path = config.get("model_paths", {}).get("silero_vad_utils", "utils/silero_vad_utils.py")
        utils_path = get_full_path(utils_path)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Silero VAD ONNX not found: {model_path}")

        logger.info(f"[VAD] Loading Silero VAD from {model_path}...")
        self.model = OnnxWrapper(model_path, force_onnx_cpu=True)
        logger.info("[VAD] Load successful.")

    def process(self, clean_audio_chunk: np.ndarray) -> tuple[float, float]:
        """
        Analyzes a clean audio chunk (numpy 1D, 16kHz).
        Returns:
            t_d (float): Total speech duration (seconds)
            t_c (float): Average VAD confidence [0, 1]
        """
        audio_tensor = torch.from_numpy(clean_audio_chunk).float()

        # Run forward pass ONLY ONCE across the entire chunk to get probabilities
        probs = self.model.audio_forward(audio_tensor, self.sr)
        
        t_c = 0.0
        t_d = 0.0
        if probs is not None and probs.numel() > 0:
            t_c = probs.mean().item()
            
            # Count the number of frames exceeding the 0.5 threshold
            active_frames = (probs > 0.5).sum().item()
            
            # Each Silero VAD frame defaults to 512 samples
            hop_length = 512
            t_d = active_frames * (hop_length / self.sr)

        return t_d, t_c
