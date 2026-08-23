"""In-Memory Audio Buffer & Async ASR Router Service."""

import asyncio
import base64
import io
import logging
from typing import Any, Optional
import httpx
import numpy as np
import scipy.io.wavfile as wavfile

logger = logging.getLogger(__name__)


def ndarray_to_wav_bytes(audio_array: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Convert float/int numpy audio array into in-memory WAV byte stream."""
    buffer = io.BytesIO()
    if audio_array.dtype == np.float32 or audio_array.dtype == np.float64:
        audio_int16 = (audio_array * 32767).clip(-32768, 32767).astype(np.int16)
    else:
        audio_int16 = audio_array.astype(np.int16)

    wavfile.write(buffer, sample_rate, audio_int16)
    return buffer.getvalue()


def b64_to_wav_bytes(b64_str: str) -> bytes:
    """Decode base64 encoded audio string to raw bytes."""
    return base64.b64decode(b64_str)


class AudioStreamRouter:
    """Routes separated audio streams to asr-module using parallel async HTTP requests."""

    def __init__(self, asr_url: str = "http://localhost:8001/api/v1/transcribe"):
        self.asr_url = asr_url

    async def transcribe_audio_async(
        self,
        client: httpx.AsyncClient,
        audio_bytes: bytes,
        filename: str = "chunk.wav",
    ) -> str:
        """Send async HTTP POST request to asr-module microservice."""
        try:
            files = {"file": (filename, audio_bytes, "audio/wav")}
            response = await client.post(self.asr_url, files=files, timeout=60.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("text", "").strip()
            else:
                logger.warning(
                    f"ASR service returned HTTP {response.status_code}: {response.text}"
                )
                return ""
        except Exception as e:
            logger.error(f"Failed to transcribe audio stream via ASR service: {e}")
            return ""

    async def route_diarized_segment(
        self,
        segment: dict[str, Any],
        sample_rate: int = 16000,
    ) -> list[dict[str, Any]]:
        """
        Route single or multiple speaker audio streams asynchronously.
        - Single Speaker: 1 async request.
        - Multiple Speakers (Overlap): Parallel async requests via asyncio.gather.
        """
        speakers = segment.get("speakers", [])
        has_overlap = segment.get("has_overlap", False)
        start_time = segment.get("start_time", 0.0)
        end_time = segment.get("end_time", 0.0)

        # Retrieve raw audio numpy arrays or base64 WAV buffers
        streams_b64 = segment.get("audio_streams_b64", [])
        raw_streams = segment.get("audio_streams", [])

        audio_bytes_list: list[bytes] = []
        if streams_b64:
            audio_bytes_list = [b64_to_wav_bytes(s) for s in streams_b64]
        elif raw_streams:
            audio_bytes_list = [
                ndarray_to_wav_bytes(arr, sample_rate) for arr in raw_streams
            ]

        if not audio_bytes_list:
            return []

        tasks = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for idx, (spk, wav_bytes) in enumerate(zip(speakers, audio_bytes_list)):
                fname = f"{spk}_segment_{idx}.wav"
                tasks.append(
                    self.transcribe_audio_async(client, wav_bytes, fname)
                )

            # Fire parallel async requests for all speaker streams
            transcripts = await asyncio.gather(*tasks)

        utterances = []
        for spk, text in zip(speakers, transcripts):
            if text:
                utterances.append({
                    "speaker_id": spk,
                    "text": text,
                    "start_time": start_time,
                    "end_time": end_time,
                    "has_overlap": has_overlap,
                })

        return utterances
