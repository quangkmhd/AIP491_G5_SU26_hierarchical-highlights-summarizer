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
        self.asr_engine: Optional[sherpa_onnx.OfflineRecognizer] = None
        self.embedding_extractor: Optional[sherpa_onnx.SpeakerEmbeddingExtractor] = None
        self.vad_window_size: int = 512  # Silero VAD at 16 kHz default
        self._init_engines()

    def _validate_paths(self) -> None:
        """Checks if all required model files exist before proceeding."""
        model_type = getattr(self.config, "model_type", "transducer")
        if model_type == "qwen3":
            required_paths = {
                "ASR Conv Frontend": self.config.qwen3_conv_frontend,
                "ASR Encoder": self.config.qwen3_encoder,
                "ASR Decoder": self.config.qwen3_decoder,
                "ASR Tokenizer": self.config.qwen3_tokenizer,
                "Silero VAD model": self.config.silero_vad,
            }
        else:
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
        """Load the OfflineRecognizer + Speaker Embedding + Silero VAD config.

        Logic copied from init_asr_engine() in the reference backend.
        """
        self._validate_paths()

        model_type = getattr(self.config, "model_type", "transducer")
        logger.info(
            "Loading OfflineRecognizer (model_type=%s, provider=%s)...",
            model_type,
            self.config.provider,
        )

        if model_type == "qwen3":
            self.asr_engine = sherpa_onnx.OfflineRecognizer.from_qwen3_asr(
                conv_frontend=self.config.qwen3_conv_frontend,
                encoder=self.config.qwen3_encoder,
                decoder=self.config.qwen3_decoder,
                tokenizer=self.config.qwen3_tokenizer,
                num_threads=self.config.num_threads,
                sample_rate=16000,
                feature_dim=128,  # Qwen3 default is 128
                decoding_method="greedy_search",  # Qwen3 default is greedy_search
                provider=self.config.provider,
            )
        else:
            self.asr_engine = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=self.config.encoder,
                decoder=self.config.decoder,
                joiner=self.config.joiner,
                tokens=self.config.tokens,
                num_threads=self.config.num_threads,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="modified_beam_search",
                provider=self.config.provider,
            )

        # Load Speaker Embedding Extractor
        if Path(self.config.speaker_embed).exists():
            logger.info("Loading Speaker Embedding Extractor (%s)...", self.config.speaker_embed)
            embedding_config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=self.config.speaker_embed,
                num_threads=1,
                provider=self.config.provider,
            )
            self.embedding_extractor = sherpa_onnx.SpeakerEmbeddingExtractor(embedding_config)
            logger.info("Speaker Embedding Extractor loaded successfully.")
        else:
            logger.warning(
                "Speaker Embedding Extractor model not found at %s. "
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
        logger.info("ASR ready. VAD window = %d samples.", self.vad_window_size)

    def create_vad(self) -> sherpa_onnx.VoiceActivityDetector:
        """Create a per-connection VAD so two clients don't cross-contaminate.

        Copied from _new_vad() in the reference backend.
        """
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = self.config.silero_vad
        cfg.silero_vad.min_silence_duration = self.config.min_silence_duration
        cfg.silero_vad.min_speech_duration = self.config.min_speech_duration
        cfg.silero_vad.max_speech_duration = self.config.max_speech_duration
        cfg.silero_vad.threshold = self.config.vad_threshold
        cfg.sample_rate = 16000
        return sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)

    def decode_segment(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Run the recognizer over one speech segment; return stripped text.

        Copied from _decode_segment() in the reference backend.
        """
        assert self.asr_engine is not None, "ASR engine not initialized"
        stream = self.asr_engine.create_stream()
        stream.accept_waveform(sample_rate, audio)

        model_type = getattr(self.config, "model_type", "transducer")
        language = getattr(self.config, "language", None)
        if model_type == "qwen3" and language:
            stream.set_option("language", language)

        self.asr_engine.decode_streams([stream])
        return stream.result.text.strip()

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
