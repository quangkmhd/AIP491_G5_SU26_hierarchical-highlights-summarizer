"""Dependency Injection Container managing system lifecycle and model initialization."""

import logging
import os
import time
import yaml

from config.paths import to_relative_path
from core.bss import ConvTasNetBSS
from core.denoiser import DeepFilterNetDenoiser
from core.embedder import CAMPlusPlusEmbedder
from core.ovd import PyannoteOVD
from core.tse import SpeakerBeamTSE
from core.vad import SileroVAD
from pipeline.audio_preprocessing import AudioPreprocessing
from pipeline.speaker_diarization import SpeakerDiarization
from state.voiceprint_pool import VoiceprintPool
from state.deferred_segment_buffer import DeferredSegmentBuffer

logger = logging.getLogger(__name__)


class DIContainer:
    """
    Container managing the lifecycle of all modules.
    Initializes AI models exactly once (Singleton behavior).
    """

    def __init__(self, config_path: str = None):
        t0 = time.perf_counter()

        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "settings.yaml")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        rel_cfg = to_relative_path(config_path)

        logger.info("=" * 65)
        logger.info(f"INITIALIZING SYSTEM — Semi RT Meeting Pipeline (Config: {rel_cfg})")
        logger.info("=" * 65)

        # --- Initialize AI Adapters (Core) ---
        t_sub = time.perf_counter()
        logger.info("[1/6] Loading DeepFilterNet Denoiser (DFN3)...")
        self.denoiser = DeepFilterNetDenoiser(self.config)
        logger.info(f"      └── DeepFilterNet Denoiser ready ({round(time.perf_counter() - t_sub, 2)}s)")

        t_sub = time.perf_counter()
        logger.info("[2/6] Loading Silero VAD (ONNX)...")
        self.vad = SileroVAD(self.config)
        logger.info(f"      └── Silero VAD ready ({round(time.perf_counter() - t_sub, 2)}s)")

        t_sub = time.perf_counter()
        logger.info("[3/6] Loading Pyannote OVD (Overlap Detection)...")
        self.ovd = PyannoteOVD(self.config)
        logger.info(f"      └── Pyannote OVD ready ({round(time.perf_counter() - t_sub, 2)}s)")

        t_sub = time.perf_counter()
        logger.info("[4/6] Loading CAM++ Voiceprint Embedder...")
        self.embedder = CAMPlusPlusEmbedder(self.config)
        logger.info(f"      └── CAM++ Embedder ready ({round(time.perf_counter() - t_sub, 2)}s)")

        t_sub = time.perf_counter()
        logger.info("[5/6] Loading SpeakerBeam TSE (Target Extraction)...")
        self.tse = SpeakerBeamTSE(self.config)
        logger.info(f"      └── SpeakerBeam TSE ready ({round(time.perf_counter() - t_sub, 2)}s)")

        t_sub = time.perf_counter()
        logger.info("[6/6] Loading Conv-TasNet BSS (Blind Source Separation)...")
        self.bss = ConvTasNetBSS(self.config)
        logger.info(f"      └── Conv-TasNet BSS ready ({round(time.perf_counter() - t_sub, 2)}s)")

        # --- Initialize State & Orchestration ---
        self.pool = VoiceprintPool(self.config)
        self.deferred_buffer = DeferredSegmentBuffer(self.config)
        self.module1 = AudioPreprocessing(self.denoiser, self.vad, self.config)
        self.module2 = SpeakerDiarization(
            self.ovd, self.embedder,
            self.tse, self.bss, self.pool, self.config,
            vad=self.vad,
            deferred_buffer=self.deferred_buffer
        )

        total_time = round(time.perf_counter() - t0, 2)
        logger.info("=" * 65)
        logger.info(f"ALL 6 AI MODELS INITIALIZED and SYSTEM READY! (Total Setup Time: {total_time}s)")
        logger.info("=" * 65)

    def reset_session(self):
        """Reset the entire pipeline state for a new meeting."""
        self.pool.reset()
        self.deferred_buffer.reset()
        self.module1.reset_session()
        self.module2.reset_session()
        logger.info("[DIContainer] Pipeline session state successfully reset.")
