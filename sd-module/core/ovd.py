"""
Core OVD \u2014 Pyannote Overlapped Speech Detection Adapter
Uses pyannote.audio.Inference with a sliding window to detect overlaps in a streaming context.
Instead of padding zeros up to 10s, it uses the actual buffer context with a 10s window and 2.5s step.
"""
import os
import torch
import numpy as np
import logging
from pyannote.audio import Model
from pyannote.audio.pipelines import OverlappedSpeechDetection
from config.paths import get_full_path

logger = logging.getLogger(__name__)


class PyannoteOVD:
    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)

        # Read OVD configuration (thresholds, duration) from config or use defaults
        ovd_cfg = config.get("module2_diarization", {}).get("ovd", {})
        self.window_duration = ovd_cfg.get("window_duration", 10.0)   # 10s context
        self.step_duration = ovd_cfg.get("step_duration", 2.5)        # 2.5s per chunk
        self.overlap_threshold = ovd_cfg.get("overlap_threshold", 0.5)
        self.onset = ovd_cfg.get("onset", 0.55)       # Threshold to consider as speaker present
        self.offset = ovd_cfg.get("offset", 0.45)     # Threshold to end (not used here)
        self.min_duration_on = ovd_cfg.get("min_duration_on", 0.1)
        self.min_duration_off = ovd_cfg.get("min_duration_off", 0.1)

        # Model path (from config or default)
        model_path = config.get("model_paths", {}).get("pyannote_segmentation", "weights/ovd.bin")
        model_path = get_full_path(model_path)

        # Check if file exists
        if not os.path.exists(model_path):
            logger.warning(f"[OVD] Model not found at {model_path}")
            self.inference = None
            self.audio_buffer = np.array([], dtype=np.float32)
            return

        try:
            model = Model.from_pretrained(model_path)
            self.pipeline = OverlappedSpeechDetection(segmentation=model)
            
            # Setup parameters (Binarize & Noise filtering)
            try:
                self.pipeline.onset = self.onset
                self.pipeline.offset = self.offset
                self.pipeline.min_duration_on = self.min_duration_on
                self.pipeline.min_duration_off = self.min_duration_off
                if hasattr(self.pipeline, 'initialize'):
                    self.pipeline.initialize()
                self.pipeline.instantiated = True
            except Exception as p_err:
                logger.warning(f"[OVD] Warning during pipeline instantiation (falling back to defaults): {p_err}")
                
            logger.info(f"[OVD] Pipeline initialized with window={self.window_duration}s, step={self.step_duration}s")
        except Exception as e:
            logger.error(f"[OVD] Failed to initialize OVD Pipeline: {e}")
            self.pipeline = None

        # Buffer for streaming audio
        self.audio_buffer = np.array([], dtype=np.float32)

    def detect_overlap(self, audio_chunk: np.ndarray) -> bool:
        """
        Detects Overlap in a clean audio chunk (numpy 1D, 16kHz).
        Uses a sliding window with buffer context.
        """
        if self.pipeline is None:
            return False

        # 1. Append chunk to buffer
        self.audio_buffer = np.concatenate([self.audio_buffer, audio_chunk])

        # 2. If buffer hasn't reached window_duration, we don't have enough context
        if len(self.audio_buffer) < int(self.sr * self.window_duration):
            return False

        # 3. Extract the exact window_duration length (take from the end to get latest context)
        context_samples = int(self.sr * self.window_duration)
        context_audio = self.audio_buffer[-context_samples:]

        # 4. Run pipeline on the context window
        try:
            # Create dictionary matching pyannote's expected format
            input_data = {
                "waveform": torch.from_numpy(context_audio).unsqueeze(0).float(),
                "sample_rate": self.sr
            }
            
            # overlap_annotation is a pyannote.core.Annotation object containing overlap segments
            overlap_annotation = self.pipeline(input_data)
            
            # Only consider the timeframe of the newest chunk (at the end of the window)
            start_time = max(0.0, self.window_duration - self.step_duration)
            end_time = self.window_duration
            
            has_overlap = False
            for segment in overlap_annotation.itersegments():
                # If the overlap region intersects with the current chunk
                if segment.end > start_time and segment.start < end_time:
                    has_overlap = True
                    break

            logger.debug(f"[OVD] Overlap detection: {has_overlap}")
            return has_overlap

        except Exception as e:
            logger.error(f"[OVD] OVD pipeline error: {e}")
            return False

        finally:
            # 5. Keep buffer size at or below window_duration to prevent memory overflow
            if len(self.audio_buffer) > int(self.sr * self.window_duration):
                self.audio_buffer = self.audio_buffer[-context_samples:]

    def reset(self):
        """Reset buffer when starting a new session (e.g., client disconnects)."""
        self.audio_buffer = np.array([], dtype=np.float32)