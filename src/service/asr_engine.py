from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import sherpa_onnx

from src.config.asr import AsrConfig

logger = logging.getLogger("src.service.asr_engine")


class AsrEngine:
    """Manages ASR + VAD + Speaker Identification engines."""

    def __init__(self, config: AsrConfig | None = None) -> None:
        self.config = config or AsrConfig()
        self.asr_engine: Optional[sherpa_onnx.OnlineRecognizer] = None
        self.embedding_extractor: Optional[sherpa_onnx.SpeakerEmbeddingExtractor] = None
        self.vad_window_size: int = 512
        self._init_engines()

    def _validate_paths(self) -> None:
        paths = [
            self.config.encoder,
            self.config.decoder,
            self.config.joiner,
            self.config.tokens,
            self.config.silero_vad,
        ]
        for p in paths:
            if not Path(p).exists():
                raise FileNotFoundError(f"Required model file not found: {p}")

    def _init_engines(self) -> None:
        self._validate_paths()
        logger.info("Loading ASR Zipformer model...")

        self.asr_engine = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=self.config.encoder,
            decoder=self.config.decoder,
            joiner=self.config.joiner,
            tokens=self.config.tokens,
            num_threads=self.config.num_threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            provider=self.config.provider,
        )

        if Path(self.config.speaker_embed).exists():
            embedding_config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=self.config.speaker_embed,
                num_threads=1,
                provider=self.config.provider,
            )
            self.embedding_extractor = sherpa_onnx.SpeakerEmbeddingExtractor(embedding_config)

    def create_vad(self) -> sherpa_onnx.VoiceActivityDetector:
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = self.config.silero_vad
        cfg.silero_vad.min_silence_duration = self.config.min_silence_duration
        cfg.silero_vad.min_speech_duration = self.config.min_speech_duration
        cfg.silero_vad.max_speech_duration = self.config.max_speech_duration
        cfg.silero_vad.threshold = self.config.vad_threshold
        cfg.sample_rate = 16000
        return sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)

    def create_stream(self) -> sherpa_onnx.OnlineStream:
        assert self.asr_engine is not None, "ASR engine not initialized"
        return self.asr_engine.create_stream()

    def decode_stream_step(
        self, stream: sherpa_onnx.OnlineStream, chunk: np.ndarray, sample_rate: int = 16000
    ) -> str:
        assert self.asr_engine is not None, "ASR engine not initialized"
        stream.accept_waveform(sample_rate, chunk)
        while self.asr_engine.is_ready(stream):
            self.asr_engine.decode_stream(stream)
        result = self.asr_engine.get_result(stream)
        text = result if isinstance(result, str) else getattr(result, "text", str(result))
        return text.strip().lower()

    def decode_segment(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        assert self.asr_engine is not None, "ASR engine not initialized"
        stream = self.create_stream()
        self.decode_stream_step(stream, audio, sample_rate)
        stream.accept_waveform(sample_rate, np.zeros(int(sample_rate * 0.4), dtype=np.float32))
        stream.input_finished()
        while self.asr_engine.is_ready(stream):
            self.asr_engine.decode_stream(stream)
        result = self.asr_engine.get_result(stream)
        text = result if isinstance(result, str) else getattr(result, "text", str(result))
        return text.strip().lower()
