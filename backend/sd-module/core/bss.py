"""Core BSS — Conv-TasNet Blind Source Separation Adapter."""

import logging
import os
import numpy as np
import torch
import torchaudio
import torchaudio.functional as F_audio
from config.paths import get_full_path, to_relative_path

logger = logging.getLogger(__name__)


class ConvTasNetBSS:
    def __init__(self, config: dict):
        self.config = config
        self.target_sr = config.get("audio", {}).get("sample_rate", 16000)
        bss_cfg = config.get("module2_diarization", {}).get("branch_c_cold_start_bss", {})
        self.model_sr = bss_cfg.get("conv_tasnet_sample_rate", 8000)
        self.device = torch.device("cpu")

        try:
            logging.getLogger("torchaudio.utils.download").setLevel(logging.WARNING)
            bss_path = config.get("model_paths", {}).get("conv_tasnet")
            if bss_path:
                bss_path = get_full_path(bss_path)

            if bss_path and os.path.exists(bss_path):
                os.environ["TORCH_HOME"] = bss_path
                rel_path = to_relative_path(bss_path)
                logger.info(f"[BSS] Conv-TasNet model loading from offline cache: '{rel_path}'...")
            else:
                logger.warning("[BSS] Offline Conv-TasNet cache directory not found. Initializing online fallback...")

            bundle = torchaudio.pipelines.CONVTASNET_BASE_LIBRI2MIX
            self.model = bundle.get_model().to(self.device)
            self.model.eval()
            self.model_sr = bundle.sample_rate
            logger.info(f"[BSS] Conv-TasNet BSS model loaded successfully (Libri2Mix, SR={self.model_sr}Hz).")
        except Exception as e:
            raise RuntimeError(f"[BSS] Critical Error: Cannot load Conv-TasNet model: {e}")

    def separate(self, mix_audio: np.ndarray) -> list[np.ndarray]:
        """Blindly separate audio mixture (16kHz) into source streams."""
        if self.model is None:
            raise RuntimeError("[BSS] Conv-TasNet model has not been initialized!")

        try:
            audio_tensor = torch.from_numpy(mix_audio).float().unsqueeze(0).unsqueeze(0)

            if self.target_sr != self.model_sr:
                audio_tensor = F_audio.resample(
                    audio_tensor, orig_freq=self.target_sr, new_freq=self.model_sr
                )

            with torch.no_grad():
                separated_sources = self.model(audio_tensor.to(self.device))

            sources_list = []
            for i in range(separated_sources.shape[1]):
                src_tensor = separated_sources[0, i:i + 1, :]

                if self.target_sr != self.model_sr:
                    src_tensor = F_audio.resample(
                        src_tensor, orig_freq=self.model_sr, new_freq=self.target_sr
                    )

                src_np = src_tensor.squeeze().cpu().numpy()

                max_val = np.max(np.abs(src_np))
                if max_val > 1.0:
                    src_np = src_np / max_val

                sources_list.append(src_np)

            return sources_list
        except Exception as e:
            logger.error(f"[BSS] Blind Source Separation failed: {e}")
            return [mix_audio]
