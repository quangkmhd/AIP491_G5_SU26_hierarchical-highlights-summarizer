"""AsrEngine -- manages ASR + VAD + Speaker Identification engines.

Copied from viet_iter3_inference/streaming_ui/backend/main.py with minimal
structural refactoring (global functions -> class methods). All inference
logic is preserved exactly as-is.

Pipeline per client connection:
  microphone (browser) --16kHz Float32--> WebSocket
       |-> Silero VAD splits stream into speech segments
            |-> OfflineRecognizer decodes each completed segment
                 |-> SpeakerEmbeddingExtractor identifies speaker
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import sherpa_onnx

from src.config.asr import AsrConfig

logger = logging.getLogger("src.service.asr_engine")


class AsrEngine:
    """Manages ASR + VAD + Speaker Identification engines.

    The recognizer is thread-safe for decode_streams; each WebSocket
    connection holds its own VAD instance so VAD state is never shared.
    """

    def __init__(self, config: AsrConfig | None = None) -> None:
        self.config = config or AsrConfig()
        self.asr_engine: Optional[sherpa_onnx.OnlineRecognizer] = None
        self.embedding_extractor: Optional[sherpa_onnx.SpeakerEmbeddingExtractor] = None
        self.vad_window_size: int = 512  # Silero VAD at 16 kHz default
        self._init_engines()

    def _validate_paths(self) -> None:
        """Checks if all required model files exist before proceeding."""
        required_paths = {
            "ASR Encoder": self.config.encoder,
            "ASR Decoder": self.config.decoder,
            "ASR Joiner": self.config.joiner,
            "ASR Tokens": self.config.tokens,
            "Silero VAD model": self.config.silero_vad,
        }
        for label, path in required_paths.items():
            if not Path(path).exists():
                logger.error("%s not found: %s", label, path)
                raise FileNotFoundError(f"{label} not found at: {path}")

    def _init_engines(self) -> None:
        """Load the OnlineRecognizer + Speaker Embedding + Silero VAD config."""
        self._validate_paths()

        model_type = getattr(self.config, "model_type", "transducer")
        logger.info(
            "ASR Model loading: Zipformer 30M-RNNT Streaming (model_type=%s, provider=%s, encoder=%s)...",
            model_type,
            self.config.provider,
            self.config.encoder,
        )

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
        logger.info("ASR Model loaded: Zipformer 30M-RNNT Streaming Transducer [provider=%s]", self.config.provider)

        # Load Speaker Embedding Extractor
        if Path(self.config.speaker_embed).exists():
            logger.info("Speaker/Diarization Model loading: WeSpeaker ResNet34 LM [path=%s]...", self.config.speaker_embed)
            embedding_config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=self.config.speaker_embed,
                num_threads=1,
                provider=self.config.provider,
            )
            self.embedding_extractor = sherpa_onnx.SpeakerEmbeddingExtractor(embedding_config)
            logger.info("Speaker/Diarization Model loaded: WeSpeaker ResNet34 LM (%s)", self.config.speaker_embed)
        else:
            logger.warning(
                "Speaker/Diarization Model (WeSpeaker ResNet34 LM) not found at %s. "
                "Diarization will be disabled.",
                self.config.speaker_embed,
            )

        # Probe the Silero VAD to learn its window size once.
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = self.config.silero_vad
        cfg.silero_vad.min_silence_duration = self.config.min_silence_duration
        cfg.silero_vad.min_speech_duration = self.config.min_speech_duration
        cfg.silero_vad.max_speech_duration = self.config.max_speech_duration
        cfg.silero_vad.threshold = self.config.vad_threshold
        cfg.sample_rate = 16000
        try:
            probe = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=1)
            self.vad_window_size = probe.config.silero_vad.window_size
            del probe
        except Exception:
            self.vad_window_size = 512
        logger.info("VAD Model ready: Silero VAD [path=%s, window=%d samples]", self.config.silero_vad, self.vad_window_size)

    def create_vad(self) -> sherpa_onnx.VoiceActivityDetector:
        """Create a per-connection VAD so two clients don't cross-contaminate."""
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = self.config.silero_vad
        cfg.silero_vad.min_silence_duration = self.config.min_silence_duration
        cfg.silero_vad.min_speech_duration = self.config.min_speech_duration
        cfg.silero_vad.max_speech_duration = self.config.max_speech_duration
        cfg.silero_vad.threshold = self.config.vad_threshold
        cfg.sample_rate = 16000
        return sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)

    def create_stream(self) -> sherpa_onnx.OnlineStream:
        """Create a per-connection online stream for continuous real-time ASR decoding."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        return self.asr_engine.create_stream()

    def decode_stream_step(
        self, stream: sherpa_onnx.OnlineStream, chunk: np.ndarray, sample_rate: int = 16000
    ) -> str:
        """Accept an audio chunk, decode ready frames, and return current partial transcript."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        stream.accept_waveform(sample_rate, chunk)
        while self.asr_engine.is_ready(stream):
            self.asr_engine.decode_stream(stream)
        result = self.asr_engine.get_result(stream)
        text = result if isinstance(result, str) else getattr(result, "text", str(result))
        return text.strip().lower()

    def reset_stream(self, stream: sherpa_onnx.OnlineStream) -> None:
        """Reset an online stream state for the next utterance."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        self.asr_engine.reset(stream)

    def decode_segment(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Run the recognizer over one speech segment; return stripped lowercase text."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        stream = self.create_stream()
        self.decode_stream_step(stream, audio, sample_rate)

        # Zipformer is chunked streaming ASR. Add the documented 0.4 s zero
        # tail and explicitly finish input so the recognizer can emit frames
        # buffered at the end of a VAD-delimited utterance.
        stream.accept_waveform(sample_rate, np.zeros(int(sample_rate * 0.4), dtype=np.float32))
        stream.input_finished()
        while self.asr_engine.is_ready(stream):
            self.asr_engine.decode_stream(stream)

        result = self.asr_engine.get_result(stream)
        text = result if isinstance(result, str) else getattr(result, "text", str(result))
        return text.strip().lower()

    def identify_speaker(
        self,
        audio: np.ndarray,
        registered_speakers: dict[str, np.ndarray],
    ) -> str:
        """Identify or register a speaker from an audio segment.

        Logic copied from send_utterance() speaker identification block
        in the reference backend.

        Args:
            audio: Float32 audio samples at 16kHz.
            registered_speakers: Mutable dict of {name: embedding}.
                New speakers are registered in-place.

        Returns:
            Speaker name (e.g. "Speaker 01").
        """
        speaker_name = "Speaker 01"
        if self.embedding_extractor is None:
            return speaker_name

        try:
            stream = self.embedding_extractor.create_stream()
            stream.accept_waveform(16000, audio)
            stream.input_finished()
            embedding = np.array(self.embedding_extractor.compute(stream), dtype=np.float32)

            # Normalize embedding
            norm_new = np.linalg.norm(embedding)
            emb_new_norm = embedding / norm_new if norm_new > 1e-6 else embedding

            # Search matching speaker
            matched_name = None
            best_score = -1.0

            for name, ref_emb in registered_speakers.items():
                norm_ref = np.linalg.norm(ref_emb)
                emb_ref_norm = ref_emb / norm_ref if norm_ref > 1e-6 else ref_emb
                score = float(np.dot(emb_new_norm, emb_ref_norm))
                logger.debug("Speaker similarity score against %s: %.4f", name, score)
                if score > best_score:
                    best_score = score
                    if score >= self.config.speaker_similarity_threshold:
                        matched_name = name

            if matched_name:
                speaker_name = matched_name
                logger.info("Speaker identified: %s (Similarity: %.4f)", speaker_name, best_score)
            else:
                new_spk_id = len(registered_speakers) + 1
                speaker_name = f"Speaker {new_spk_id:02d}"
                registered_speakers[speaker_name] = embedding
                logger.info("New speaker registered: %s (Best score: %.4f)", speaker_name, best_score)
        except Exception as e:
            logger.exception("Error during real-time speaker identification: %s", e)

        return speaker_name
