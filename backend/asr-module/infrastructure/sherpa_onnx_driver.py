"""Sherpa-ONNX ASR Driver implementation."""

import os
import threading
from typing import Optional
import numpy as np
import sherpa_onnx

from config import settings
from domain.entities import TranscriptionResult
from domain.interfaces import ASRModelInterface
from infrastructure.logger import logger


class SherpaOnnxASRDriver(ASRModelInterface):
    def __init__(self):
        self._recognizer: Optional[sherpa_onnx.OfflineRecognizer] = None
        self._lock = threading.Lock()
        self._load_model()

    def _load_model(self):
        logger.info("Initializing Sherpa-ONNX Offline Recognizer...")
        
        # Verify required model files exist
        for path_name, path_val in [
            ("Encoder", settings.MODEL_ENCODER_PATH),
            ("Decoder", settings.MODEL_DECODER_PATH),
            ("Joiner", settings.MODEL_JOINER_PATH),
            ("Tokens", settings.TOKENS_PATH),
        ]:
            if not os.path.exists(path_val):
                logger.error(f"{path_name} file not found at: {path_val}")
                raise FileNotFoundError(f"Missing required model artifact: {path_val}")

        try:
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=settings.MODEL_ENCODER_PATH,
                decoder=settings.MODEL_DECODER_PATH,
                joiner=settings.MODEL_JOINER_PATH,
                tokens=settings.TOKENS_PATH,
                num_threads=settings.NUM_THREADS,
                sample_rate=settings.SAMPLE_RATE,
                decoding_method=settings.DECODING_METHOD,
            )
            logger.info("Sherpa-ONNX Model loaded successfully!")
        except Exception as e:
            logger.critical(f"Failed to load Sherpa-ONNX model: {e}")
            raise RuntimeError(f"Sherpa-ONNX initialization failed: {e}")

    def is_ready(self) -> bool:
        return self._recognizer is not None

    def transcribe_waveform(
        self, samples: np.ndarray, sample_rate: int, filename: Optional[str] = None
    ) -> TranscriptionResult:
        if not self.is_ready():
            raise RuntimeError("ASR Model is not initialized.")

        duration = float(len(samples) / sample_rate)
        
        with self._lock:
            stream = self._recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples)
            self._recognizer.decode_stream(stream)
            # Convert output text to lowercase
            text = stream.result.text.strip().lower()

        return TranscriptionResult(
            text=text,
            duration_seconds=round(duration, 2),
            sample_rate=sample_rate,
            filename=filename,
            status="success"
        )
