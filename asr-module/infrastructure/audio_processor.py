"""Audio Processing Utility."""

import io
from typing import Tuple
import numpy as np
import soundfile as sf
from infrastructure.logger import logger


class AudioProcessor:
    @staticmethod
    def load_audio_from_bytes(audio_bytes: bytes, target_sample_rate: int = 16000) -> Tuple[np.ndarray, int, float]:
        """Loads audio bytes, converts to float32 mono, and returns (samples, sample_rate, duration)."""
        try:
            byte_io = io.BytesIO(audio_bytes)
            data, sample_rate = sf.read(byte_io, dtype="float32")
            
            # Convert multi-channel to mono
            if len(data.shape) > 1:
                data = data.mean(axis=1)

            # Simple linear resampling if sample rate doesn't match target
            if sample_rate != target_sample_rate:
                logger.warning(
                    f"Sample rate mismatch: received {sample_rate}Hz, resampling to {target_sample_rate}Hz"
                )
                num_target_samples = int(len(data) * target_sample_rate / sample_rate)
                data = np.interp(
                    np.linspace(0, len(data), num_target_samples, endpoint=False),
                    np.arange(len(data)),
                    data
                ).astype(np.float32)
                sample_rate = target_sample_rate

            duration = float(len(data) / sample_rate)
            return data, sample_rate, duration
        except Exception as e:
            logger.error(f"Error processing audio bytes: {e}")
            raise ValueError(f"Failed to decode audio file format: {e}")
