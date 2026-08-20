"""
Core Denoiser \u2014 DeepFilterNet3 Adapter
Cleans up the audio signal, removing background noise.
Pipeline: Upsample 48kHz \u2192 DFN Enhance \u2192 Downsample 16kHz
"""
import torch
import os
import torchaudio
import numpy as np
import logging
from df.enhance import init_df, enhance
from config.paths import get_full_path

logger = logging.getLogger(__name__)


class DeepFilterNetDenoiser:
    def __init__(self, config: dict):
        self.config = config
        self.target_sr = config.get("audio", {}).get("sample_rate", 16000)

        denoiser_cfg = config.get("module1_preprocessing", {}).get("denoiser", {})
        self.atten_lim_db = denoiser_cfg.get("atten_lim_db", 15.0)
        post_filter = denoiser_cfg.get("post_filter", False)

        dfn_path = config.get("model_paths", {}).get("deepfilternet")
        if dfn_path:
            dfn_path = get_full_path(dfn_path)

        if dfn_path and os.path.exists(dfn_path):
            logger.info(f"[Denoiser] Loading DeepFilterNet3 from offline directory: {dfn_path}...")
            self.model, self.df_state, _ = init_df(model_base_dir=dfn_path, post_filter=post_filter)
        else:
            logger.warning("[Denoiser] Offline DFN directory not found. Downloading from internet...")
            self.model, self.df_state, _ = init_df(post_filter=post_filter)
            
        self.model_sr = self.df_state.sr()  # Always 48000
        logger.info(f"[Denoiser] Load successful. DFN SR={self.model_sr}Hz, Target={self.target_sr}Hz")

    def process(self, audio_chunk: np.ndarray) -> np.ndarray:
        """
        Takes a 1D numpy audio chunk (16kHz), denoises it, and returns a clean 1D chunk (16kHz).
        Pipeline: 16kHz \u2192 48kHz \u2192 Enhance \u2192 48kHz \u2192 16kHz
        """
        # Convert numpy to tensor [1, T]
        audio_tensor = torch.from_numpy(audio_chunk).float().unsqueeze(0)

        # 1. Upsample to 48kHz (required for DFN)
        if self.target_sr != self.model_sr:
            audio_tensor = torchaudio.functional.resample(
                audio_tensor, orig_freq=self.target_sr, new_freq=self.model_sr
            )

        # 2. Enhance (wrap in no_grad to prevent RAM leakage)
        with torch.no_grad():
            clean_tensor = enhance(
                self.model, self.df_state, audio_tensor,
                atten_lim_db=self.atten_lim_db
            )

        # 3. Downsample back to 16kHz
        if self.model_sr != self.target_sr:
            clean_tensor = torchaudio.functional.resample(
                clean_tensor, orig_freq=self.model_sr, new_freq=self.target_sr
            )

        return clean_tensor.squeeze(0).cpu().numpy()
