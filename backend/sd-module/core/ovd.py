"""Core OVD — Pyannote Overlapped Speech Detection Adapter."""

import logging
import os
import numpy as np
from pyannote.audio import Model
from pyannote.audio.pipelines import OverlappedSpeechDetection
from config.paths import get_full_path, to_relative_path

logger = logging.getLogger(__name__)


class PyannoteOVD:
    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)

        ovd_cfg = config.get("module2_diarization", {}).get("ovd", {})
        self.window_duration = ovd_cfg.get("window_duration", 10.0)
        self.step_duration = ovd_cfg.get("step_duration", 2.5)
        self.overlap_threshold = ovd_cfg.get("overlap_threshold", 0.5)
        self.onset = ovd_cfg.get("onset", 0.55)
        self.offset = ovd_cfg.get("offset", 0.45)
        self.min_duration_on = ovd_cfg.get("min_duration_on", 0.1)
        self.min_duration_off = ovd_cfg.get("min_duration_off", 0.1)

        model_path = config.get("model_paths", {}).get("pyannote_segmentation", "weights/ovd.bin")
        model_path = get_full_path(model_path)

        if not os.path.exists(model_path):
            rel_path = to_relative_path(model_path)
            logger.warning(f"[OVD] Checkpoint not found at: '{rel_path}'. Overlap detection disabled.")
            self.inference = None
            self.audio_buffer = np.array([], dtype=np.float32)
            return

        try:
            rel_path = to_relative_path(model_path)
            logger.info(f"[OVD] Loading Pyannote OVD checkpoint from: '{rel_path}'...")
            model = Model.from_pretrained(model_path)
            self.pipeline = OverlappedSpeechDetection(segmentation=model)

            try:
                self.pipeline.onset = self.onset
                self.pipeline.offset = self.offset
                self.pipeline.min_duration_on = self.min_duration_on
                self.pipeline.min_duration_off = self.min_duration_off
                if hasattr(self.pipeline, "initialize"):
                    self.pipeline.initialize()
            except Exception as p_err:
                logger.debug(f"[OVD] Note on pipeline instantiation: {p_err}")

            logger.info(
                f"[OVD] Pyannote OVD loaded (Window: {self.window_duration}s, Step: {self.step_duration}s, "
                f"Threshold: {self.overlap_threshold})."
            )
        except Exception as e:
            logger.error(f"[OVD] Failed to initialize Pyannote OVD: {e}")
            self.pipeline = None

        self.audio_buffer = np.array([], dtype=np.float32)

    def reset(self):
        """Reset the internal rolling audio buffer for a new meeting session."""
        self.audio_buffer = np.array([], dtype=np.float32)

    def detect_overlap(self, clean_chunk: np.ndarray) -> bool:
        """Detect whether the current clean audio chunk contains overlapping speech."""
        if self.pipeline is None:
            return False

        self.audio_buffer = np.concatenate([self.audio_buffer, clean_chunk])
        max_samples = int(self.window_duration * self.sr)
        if len(self.audio_buffer) > max_samples:
            self.audio_buffer = self.audio_buffer[-max_samples:]

        if len(self.audio_buffer) < int(0.5 * self.sr):
            return False

        try:
            import torch
            audio_tensor = torch.from_numpy(self.audio_buffer).float().unsqueeze(0)
            file_dict = {"waveform": audio_tensor, "sample_rate": self.sr}

            output = self.pipeline(file_dict)
            has_overlap = False

            if hasattr(output, "get_timeline"):
                timeline = output.get_timeline()
                overlap_dur = sum(segment.duration for segment in timeline)
                has_overlap = overlap_dur > 0.1
            elif hasattr(output, "extent"):
                has_overlap = len(output) > 0

            return has_overlap
        except Exception as e:
            logger.warning(f"[OVD] Overlap detection error: {e}")
            return False