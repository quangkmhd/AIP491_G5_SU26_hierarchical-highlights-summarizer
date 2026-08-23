"""Core TSE — SpeakerBeam-SS Target Speaker Extraction Adapter."""

import logging
import os
import numpy as np
import torch
from config.paths import get_full_path, to_relative_path

logger = logging.getLogger(__name__)


class SpeakerBeamTSE:
    """
    Target Speaker Extraction using SpeakerBeam-SS.
    Interface: extract_targets(mix_audio, profile1, profile2)
        → List[Tuple[np.ndarray, bool]]  # [(separated_audio, is_valid), ...]
    """

    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)
        self.model = None
        self.speaker_encoder = None

        checkpoint_path = config.get("model_paths", {}).get("speakerbeam_checkpoint")
        if checkpoint_path:
            checkpoint_path = get_full_path(checkpoint_path)

        if checkpoint_path and os.path.exists(checkpoint_path):
            try:
                from utils.speakerbeam import SpeakerBeamSS

                self.device = torch.device("cpu")
                self.model = SpeakerBeamSS()
                state_dict = torch.load(checkpoint_path, map_location=self.device)

                in_conv_weight = state_dict.get("separator.in_conv1x1.weight")
                if in_conv_weight is not None:
                    expected_dim = in_conv_weight.shape[0]
                    if expected_dim != 256:
                        raise ValueError(
                            f"Model embedding dimension ({expected_dim}) DOES NOT MATCH requirement (256-dim)."
                        )

                self.model.load_state_dict(state_dict)
                self.model.eval()

                rel_path = to_relative_path(checkpoint_path)
                logger.info(f"[TSE] SpeakerBeam-SS model checkpoint loaded from: '{rel_path}'")
            except Exception as e:
                logger.error(f"[TSE] Failed to load SpeakerBeam-SS checkpoint: {e}")
                self.model = None
        else:
            rel_path = to_relative_path(checkpoint_path) if checkpoint_path else "None"
            logger.warning(f"[TSE] Checkpoint not found at: '{rel_path}'. TSE separation disabled.")

        try:
            from resemblyzer import VoiceEncoder
            self.speaker_encoder = VoiceEncoder()
            logger.info("[TSE] Resemblyzer VoiceEncoder (256-dim d-vector) initialized for target extraction.")
        except Exception as e:
            logger.error(f"[TSE] Failed to load Resemblyzer VoiceEncoder: {e}")
            self.speaker_encoder = None

    def extract_targets(self, mix_audio: np.ndarray, profile1: dict, profile2: dict) -> list[tuple[np.ndarray, bool]]:
        """Extract separated audio streams for target speaker profiles."""
        if self.model is None or self.speaker_encoder is None:
            logger.warning("[TSE] SpeakerBeam model or Resemblyzer encoder not initialized. Skipping TSE.")
            return [(mix_audio, False)]

        separated_results = []
        profiles = [("Speaker_01", profile1), ("Speaker_02", profile2)]

        for spk_name, prof in profiles:
            if not prof:
                continue

            try:
                ref_audio = prof.get("reference_audio")
                if ref_audio is None or len(ref_audio) < int(0.5 * self.sr):
                    continue

                d_vector = self.speaker_encoder.embed_utterance(ref_audio)
                d_tensor = torch.from_numpy(d_vector).float().unsqueeze(0).to(self.device)

                mix_tensor = torch.from_numpy(mix_audio).float().unsqueeze(0).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    est_sources = self.model(mix_tensor, d_tensor)

                est_audio = est_sources.squeeze().cpu().numpy()

                max_val = np.max(np.abs(est_audio))
                if max_val > 1.0:
                    est_audio = est_audio / max_val

                separated_results.append((est_audio, True))
            except Exception as e:
                logger.error(f"[TSE] Target extraction failed for {spk_name}: {e}")

        if not separated_results:
            separated_results.append((mix_audio, False))

        return separated_results
