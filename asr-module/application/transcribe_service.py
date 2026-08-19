"""Transcription Application Use Case."""

from domain.entities import TranscriptionResult
from domain.interfaces import ASRModelInterface
from infrastructure.audio_processor import AudioProcessor
from infrastructure.logger import logger


class TranscribeAudioUseCase:
    def __init__(self, model_driver: ASRModelInterface):
        self.model_driver = model_driver

    def execute(self, audio_bytes: bytes, filename: str = "audio.wav") -> TranscriptionResult:
        logger.info(f"Received transcription request for file: '{filename}' ({len(audio_bytes)} bytes)")
        
        # 1. Preprocess Audio
        samples, sample_rate, duration = AudioProcessor.load_audio_from_bytes(audio_bytes)
        
        # 2. Perform ASR Inference
        result = self.model_driver.transcribe_waveform(
            samples=samples,
            sample_rate=sample_rate,
            filename=filename
        )
        
        logger.info(
            f"Successfully transcribed '{filename}' (Duration: {duration:.2f}s) -> "
            f"Result: '{result.text}'"
        )
        return result
