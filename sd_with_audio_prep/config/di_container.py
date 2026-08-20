"""Dependency Injection Container"""
import os
import yaml
import logging

from core.denoiser import DeepFilterNetDenoiser
from core.vad import SileroVAD
from core.ovd import PyannoteOVD
from core.embedder import CAMPlusPlusEmbedder
from core.tse import SpeakerBeamTSE
from core.bss import ConvTasNetBSS

from pipeline.audio_preprocessing import AudioPreprocessing
from pipeline.speaker_diarization import SpeakerDiarization
from state.voiceprint_pool import VoiceprintPool

logger = logging.getLogger(__name__)


class DIContainer:
    """
    Container managing the lifecycle of all modules.
    Initializes AI models exactly once (Singleton behavior).
    """

    def __init__(self, config_path: str = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "settings.yaml")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        logger.info("=" * 60)
        logger.info("INITIALIZING SYSTEM \u2014 Semi RT Meeting Pipeline")
        logger.info("=" * 60)

        # --- Initialize AI Adapters (Core) ---
        logger.info("\n[1/6] Initializing DeepFilterNet Denoiser...")
        self.denoiser = DeepFilterNetDenoiser(self.config)

        logger.info("[2/6] Initializing Silero VAD...")
        self.vad = SileroVAD(self.config)

        logger.info("[3/6] Initializing Pyannote OVD...")
        self.ovd = PyannoteOVD(self.config)

        logger.info("[4/6] Initializing CAM++ Embedder...")
        self.embedder = CAMPlusPlusEmbedder(self.config)

        logger.info("[5/6] Initializing SpeakerBeam TSE...")
        self.tse = SpeakerBeamTSE(self.config)

        logger.info("[6/6] Initializing Conv-TasNet BSS...")
        self.bss = ConvTasNetBSS(self.config)

        # --- Initialize State ---
        self.pool = VoiceprintPool(self.config)

        # --- Initialize Pipeline Orchestration ---
        self.module1 = AudioPreprocessing(self.denoiser, self.vad, self.config)
        self.module2 = SpeakerDiarization(
            self.ovd, self.embedder,
            self.tse, self.bss, self.pool, self.config,
            vad=self.vad
        )

        logger.info("=" * 60)
        logger.info("SYSTEM READY!")
        logger.info("=" * 60)

    def reset_session(self):
        """Reset the entire pipeline state for a new meeting."""
        self.pool.reset()
        self.module1.reset_session()
        self.module2.reset_session()
        logger.info("[DIContainer] Completely reset the system for a new session.")
