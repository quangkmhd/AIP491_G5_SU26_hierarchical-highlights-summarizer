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
        """Khởi tạo công cụ nhận dạng tiếng nói ASR, VAD và nhận diện người nói."""
        self.config = config or AsrConfig()
        self.asr_engine: Optional[sherpa_onnx.OnlineRecognizer] = None
        self.embedding_extractor: Optional[sherpa_onnx.SpeakerEmbeddingExtractor] = None
        self.vad_window_size: int = 512  # Silero VAD at 16 kHz default
        self._init_engines()

    def _validate_paths(self) -> None:
        """Kiểm tra sự tồn tại của các tệp mô hình ASR và VAD bắt buộc."""
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
        """Nạp các mô hình OnlineRecognizer, SpeakerEmbeddingExtractor và cấu hình VAD."""
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

        # Nạp mô hình trích xuất đặc trưng người nói (Speaker Embedding Extractor)
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

        # Thử nghiệm Silero VAD để xác định kích thước cửa sổ xử lý (window size)
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
        """Tạo đối tượng phát hiện khoảng lặng VAD riêng biệt cho từng kết nối WebSocket."""
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = self.config.silero_vad
        cfg.silero_vad.min_silence_duration = self.config.min_silence_duration
        cfg.silero_vad.min_speech_duration = self.config.min_speech_duration
        cfg.silero_vad.max_speech_duration = self.config.max_speech_duration
        cfg.silero_vad.threshold = self.config.vad_threshold
        cfg.sample_rate = 16000
        return sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)

    def create_stream(self) -> sherpa_onnx.OnlineStream:
        """Tạo luồng nhận dạng trực tuyến phục vụ giải mã ASR real-time."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        return self.asr_engine.create_stream()

    def decode_stream_step(
        self, stream: sherpa_onnx.OnlineStream, chunk: np.ndarray, sample_rate: int = 16000
    ) -> str:
        """Nạp một khung âm thanh, giải mã các khung đã sẵn sàng và trả về chuỗi văn bản tạm thời."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        stream.accept_waveform(sample_rate, chunk)
        while self.asr_engine.is_ready(stream):
            self.asr_engine.decode_stream(stream)
        result = self.asr_engine.get_result(stream)
        text = result if isinstance(result, str) else getattr(result, "text", str(result))
        return text.strip().lower()

    def reset_stream(self, stream: sherpa_onnx.OnlineStream) -> None:
        """Đặt lại trạng thái luồng giải mã ASR cho câu thoại tiếp theo."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        self.asr_engine.reset(stream)

    def decode_segment(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Giải mã một đoạn âm thanh tiếng nói hoàn chỉnh và trả về văn bản dạng chữ thường."""
        assert self.asr_engine is not None, "ASR engine not initialized"
        stream = self.create_stream()
        self.decode_stream_step(stream, audio, sample_rate)

        # Bổ sung khoảng đệm đuôi 0.4s và kết thúc đầu vào để mô hình Zipformer phát nốt các khung hình còn lại.
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
        """Nhận diện người nói hoặc đăng ký người nói mới từ đoạn âm thanh."""
        speaker_name = "Speaker 01"
        if self.embedding_extractor is None:
            return speaker_name

        try:
            stream = self.embedding_extractor.create_stream()
            stream.accept_waveform(16000, audio)
            stream.input_finished()
            embedding = np.array(self.embedding_extractor.compute(stream), dtype=np.float32)

            # Chuẩn hóa vectơ nhúng (embedding normalization)
            norm_new = np.linalg.norm(embedding)
            emb_new_norm = embedding / norm_new if norm_new > 1e-6 else embedding

            # Tìm kiếm người nói khớp nhất trong danh sách đã đăng ký
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
