"""Core Denoiser — DeepFilterNet3 Adapter."""

import logging
import os
# pyrefly: ignore [missing-import]
from df.enhance import enhance, init_df
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
import torchaudio
from config.paths import get_full_path, to_relative_path

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

        try:

            # pyrefly: ignore [missing-import]
            from loguru import logger as loguru_logger
            loguru_logger.remove()
            # pyrefly: ignore [missing-import]
            import df.logger
            df.logger._logger_initialized = True
        except Exception:
            pass

        if dfn_path and os.path.exists(dfn_path):
            rel_path = to_relative_path(dfn_path)
            logger.info(f"[Denoiser] Model checkpoint loaded from relative path: '{rel_path}'")
            self.model, self.df_state, _ = init_df(model_base_dir=dfn_path, post_filter=post_filter)
        else:
            logger.warning("[Denoiser] Offline DFN checkpoint directory not found. Initializing online fallback...")
            self.model, self.df_state, _ = init_df(post_filter=post_filter)

        try:
            # pyrefly: ignore [missing-import]
            from loguru import logger as loguru_logger
            loguru_logger.remove()
        except ImportError:
            pass

        self.model_sr = self.df_state.sr()  # Always 48000
        logger.info(f"[Denoiser] DFN3 Engine active (Model SR: {self.model_sr}Hz, Target SR: {self.target_sr}Hz).")

    def process(self, audio_chunk: np.ndarray) -> np.ndarray:
        """Denoise 16kHz audio chunk: 16kHz → 48kHz → DFN Enhance → 16kHz."""
        audio_tensor = torch.from_numpy(audio_chunk).float().unsqueeze(0)

        if self.target_sr != self.model_sr:
            audio_tensor = torchaudio.functional.resample(
                audio_tensor, orig_freq=self.target_sr, new_freq=self.model_sr
            )

        with torch.no_grad():
            clean_tensor = enhance(
                self.model, self.df_state, audio_tensor,
                atten_lim_db=self.atten_lim_db
            )

        if self.target_sr != self.model_sr:
            clean_tensor = torchaudio.functional.resample(
                clean_tensor, orig_freq=self.model_sr, new_freq=self.target_sr
            )

        return clean_tensor.squeeze(0).numpy()
