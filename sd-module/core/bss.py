"""
Core BSS \u2014 Conv-TasNet Blind Source Separation Adapter
Blindly separates an audio mixture into source streams (Branch C - Cold Start).
Uses torchaudio pre-trained Conv-TasNet (8kHz) + resamples output to 16kHz.
"""
import os
import torch
import torchaudio
import torchaudio.functional as F_audio
import numpy as np
import logging
from config.paths import get_full_path

logger = logging.getLogger(__name__)


class ConvTasNetBSS:
    def __init__(self, config: dict):
        self.config = config
        self.target_sr = config.get("audio", {}).get("sample_rate", 16000)
        bss_cfg = config.get("module2_diarization", {}).get("branch_c_cold_start_bss", {})
        self.model_sr = bss_cfg.get("conv_tasnet_sample_rate", 8000)
        self.device = torch.device("cpu")  # CPU-first

        try:
            bss_path = config.get("model_paths", {}).get("conv_tasnet")
            if bss_path:
                bss_path = get_full_path(bss_path)
                
            if bss_path and os.path.exists(bss_path):
                os.environ["TORCH_HOME"] = bss_path
                logger.info(f"[BSS] Loading Conv-TasNet from torchaudio (Offline TORCH_HOME: {bss_path})...")
            else:
                logger.warning(f"[BSS] Offline TORCH_HOME directory not found. Downloading from internet...")

            bundle = torchaudio.pipelines.CONVTASNET_BASE_LIBRI2MIX
            self.model = bundle.get_model().to(self.device)
            self.model.eval()
            # Retrieve standard sample rate from bundle
            self.model_sr = bundle.sample_rate
            logger.info(f"[BSS] Load successful. Model SR={self.model_sr}Hz")
        except Exception as e:
            raise RuntimeError(f"[BSS] Critical Error: Cannot load Conv-TasNet: {e}")

    def separate(self, mix_audio: np.ndarray) -> list[np.ndarray]:
        """
        Blindly separates the audio mixture (numpy 1D, 16kHz) into source streams.
        Returns a list of 1D numpy arrays at 16kHz.
        """
        logger.info(f"[BSS] Input shape: {mix_audio.shape}, dtype: {mix_audio.dtype}")
        if self.model is None:
            raise RuntimeError("[BSS] Conv-TasNet has not been initialized!")

        try:
            # Convert to tensor [1, 1, T] (Batch, Channel, Samples)
            audio_tensor = torch.from_numpy(mix_audio).float().unsqueeze(0).unsqueeze(0)

            # 1. Downsample 16kHz \u2192 model_sr (8kHz)
            if self.target_sr != self.model_sr:
                audio_tensor = F_audio.resample(
                    audio_tensor.squeeze(0),  # [1, T]
                    orig_freq=self.target_sr,
                    new_freq=self.model_sr
                ).unsqueeze(0)  # [1, 1, T]

            # 2. Amplitude normalization
            max_val = torch.max(torch.abs(audio_tensor))
            if max_val > 0:
                audio_tensor = audio_tensor / (max_val + 1e-8)

            # 3. Inference
            with torch.no_grad():
                separated = self.model(audio_tensor)  # Shape: (1, C, T) where C=2 sources

            # 4. Denormalize
            separated = separated * max_val

            # 5. Upsample each stream back to 16kHz
            results = []
            num_sources = separated.shape[1]
            for i in range(num_sources):
                source = separated[0, i:i+1, :]  # [1, T]
                if self.model_sr != self.target_sr:
                    source = F_audio.resample(
                        source, orig_freq=self.model_sr, new_freq=self.target_sr
                    )
                results.append(source.squeeze(0).cpu().numpy())
            
            logger.info(f"[BSS] Output: {len(results)} streams, shapes: {[r.shape for r in results]}")
            return results

        except Exception as e:
            logger.error(f"[BSS] Source separation error: {e}")
            return []
