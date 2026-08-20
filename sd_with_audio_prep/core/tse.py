"""
Core TSE \u2014 SpeakerBeam-SS Target Speaker Extraction Adapter
Extracts the target speaker based on speaker enrollment (Branch B).

SpeakerBeam-SS uses Resemblyzer VoiceEncoder (256-dim d-vector)
to create the enrollment embedding, unlike CAM++ (192-dim) used for matching.
Therefore, this adapter manages the creation of enrollment embeddings 
from the raw audio stored in the pool.
"""
import numpy as np
import logging
import os
import sys
from typing import Optional
from config.paths import get_full_path

logger = logging.getLogger(__name__)


class SpeakerBeamTSE:
    """
    Target Speaker Extraction using SpeakerBeam-SS.
    Interface: extract_targets(mix_audio, profile1, profile2)
        \u2192 List[Tuple[np.ndarray, bool]]  # [(separated_audio, is_valid), ...]
    """

    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)
        self.model = None
        self.speaker_encoder = None  # Resemblyzer VoiceEncoder

        checkpoint_path = config.get("model_paths", {}).get("speakerbeam_checkpoint")

        # Resolve relative path
        if checkpoint_path and not os.path.isabs(checkpoint_path):
            base_dir = os.path.join(os.path.dirname(__file__), "..")
            checkpoint_path = os.path.abspath(os.path.join(base_dir, checkpoint_path))

        if checkpoint_path and os.path.exists(checkpoint_path):
            try:
                import torch

                from utils.speakerbeam import SpeakerBeamSS

                self.device = torch.device("cpu")
                self.model = SpeakerBeamSS()
                state_dict = torch.load(checkpoint_path, map_location=self.device)
                
                # Check model embedding size compatibility
                in_conv_weight = state_dict.get('separator.in_conv1x1.weight')
                if in_conv_weight is not None:
                    expected_dim = in_conv_weight.shape[0]  # out_channels
                    if expected_dim != 256:
                        raise ValueError(f"Model embedding dimension ({expected_dim}) DOES NOT MATCH the system requirement (256-dim).")

                self.model.load_state_dict(state_dict)
                self.model.eval()
                logger.info(f"[TSE] SpeakerBeam-SS successfully loaded from {checkpoint_path}")

                # Initialize Resemblyzer VoiceEncoder for enrollment embedding
                from resemblyzer import VoiceEncoder
                weights_fpath = self.config.get("model_paths", {}).get("resemblyzer")
                if weights_fpath:
                    weights_fpath = get_full_path(weights_fpath)
                
                if weights_fpath and os.path.exists(weights_fpath):
                    self.speaker_encoder = VoiceEncoder(device="cpu", weights_fpath=weights_fpath)
                    logger.info(f"[TSE] Resemblyzer VoiceEncoder successfully loaded from {weights_fpath}")
                else:
                    raise FileNotFoundError(f"[TSE] Critical Error: Resemblyzer offline weights not found at {weights_fpath}")
            except Exception as e:
                raise RuntimeError(f"[TSE] Critical Error initializing SpeakerBeam-SS or Resemblyzer: {e}")
        else:
            raise FileNotFoundError(f"[TSE] Critical Error: SpeakerBeam checkpoint does not exist: {checkpoint_path}")

    def _get_enrollment_embedding(self, enrollment_audio: np.ndarray) -> np.ndarray:
        """
        Extracts the Resemblyzer d-vector (256-dim) from the enrollment audio.
        """
        import torch
        from resemblyzer import preprocess_wav

        processed = preprocess_wav(enrollment_audio)
        emb = self.speaker_encoder.embed_utterance(processed)
        return torch.from_numpy(emb).float().unsqueeze(0).to(self.device)  # (1, 256)

    def extract_targets(
        self,
        mix_audio: np.ndarray,
        profile1: Optional[dict],
        profile2: Optional[dict]
    ) -> list[tuple[np.ndarray, bool]]:
        """
        Extracts target speakers from the mixture based on 2 speaker profiles.

        Args:
            mix_audio: Audio mixture chunk (numpy 1D, 16kHz)
            profile1: Dict containing {"embedding": np.ndarray, ...} of speaker 1
            profile2: Dict containing {"embedding": np.ndarray, ...} of speaker 2

        Returns:
            List of (separated_audio, is_valid) tuples.
            is_valid = True if the separated stream has sufficient quality.
        """
        # If the model hasn't loaded or VoiceEncoder is missing, extraction fails
        if self.model is None or self.speaker_encoder is None:
            raise RuntimeError("[TSE] Model not initialized, cannot extract.")

        try:
            import torch

            # Prepare mix audio tensor: (1, 1, T)
            mix_tensor = torch.from_numpy(mix_audio).float()
            mix_tensor = mix_tensor.unsqueeze(0).unsqueeze(0).to(self.device)

            results = []
            for profile in [profile1, profile2]:
                if profile is None:
                    continue

                # Use reference audio (clean audio) from VoiceprintPool to create enrollment
                ref_audio = profile.get("reference_audio")
                if ref_audio is None:
                    logger.warning("[TSE] Profile has no reference_audio, using mix_audio (less accurate).")
                    ref_audio = mix_audio

                enrollment_emb = self._get_enrollment_embedding(ref_audio)

                with torch.no_grad():
                    separated = self.model(mix_tensor, enrollment_emb)  # (1, 1, T')

                sep_audio = separated.squeeze().cpu().numpy()

                # Validate: check minimum energy
                energy = np.sqrt(np.mean(sep_audio ** 2))
                is_valid = energy > 0.01  # Minimum energy threshold

                results.append((sep_audio, is_valid))

            return results

        except Exception as e:
            logger.error(f"[TSE] Inference error: {e}")
            return []
