"""FastAPI Web Server for Standalone Speaker Diarization Microservice (sd-module)."""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*weights_only=False.*")

import logging
# Mute noise from 3rd party model libraries
for lib in ["modelscope", "DF", "matplotlib", "pyannote", "lightning", "torchaudio"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

import base64
from contextlib import asynccontextmanager
import io
from typing import Any
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal
import soundfile as sf

from config.di_container import DIContainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sd_module.api")

import shutil
import subprocess

# Global container instance
container_instance: DIContainer | None = None


def load_audio_bytes(contents: bytes, target_sr: int = 16000) -> np.ndarray:
    """Robustly load audio bytes (WAV, WebM, OGG, MP3, FLAC, M4A) and return 16kHz mono float32 array."""
    # Attempt 1: soundfile (WAV, FLAC, OGG)
    try:
        audio, orig_sr = sf.read(io.BytesIO(contents))
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        if orig_sr != target_sr:
            num_samples = int(len(audio) * target_sr / orig_sr)
            audio = signal.resample(audio, num_samples)
        return audio.astype(np.float32)
    except Exception:
        pass

    # Attempt 2: ffmpeg subprocess (WebM, OGG, MP3, M4A)
    ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg" or "/usr/local/bin/ffmpeg"
    try:
        proc = subprocess.Popen(
            [ffmpeg_bin, "-i", "pipe:0", "-f", "wav", "-ar", str(target_sr), "-ac", "1", "pipe:1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate(input=contents)
        if proc.returncode == 0 and len(out) > 0:
            audio, _ = sf.read(io.BytesIO(out))
            return audio.astype(np.float32)
        else:
            logger.warning(f"ffmpeg conversion error: {err.decode('utf-8', errors='ignore')}")
    except Exception as ex:
        logger.warning(f"ffmpeg invocation failed: {ex}")

    raise ValueError("Unrecognized audio format. Please provide valid WAV, WebM, OGG, or MP3 audio.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load AI models once on server startup."""
    global container_instance
    logger.info("Starting up Speaker Diarization Microservice...")
    try:
        container_instance = DIContainer()
        app.state.container = container_instance
        logger.info("Speaker Diarization Microservice initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to load Speaker Diarization models: {e}")
        container_instance = None
    yield
    logger.info("Shutting down Speaker Diarization Microservice.")


def create_app() -> FastAPI:
    """Initialize FastAPI App for sd-module."""
    app = FastAPI(
        title="Speaker Diarization Microservice",
        version="1.0.0",
        description="Target Diarization Pipeline (Silero VAD + Conv-TasNet BSS + SpeakerBeam TSE + CAM++)",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def health_check() -> dict[str, Any]:
        """Readiness and liveness check probe."""
        is_ready = container_instance is not None
        return {
            "status": "ready" if is_ready else "not_ready",
            "service": "Speaker Diarization Microservice",
        }

    @app.post("/api/v1/diarize")
    async def diarize_audio(file: UploadFile = File(...)) -> dict[str, Any]:
        """Process an uploaded audio file and return diarization segments with separated streams."""
        if container_instance is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Speaker Diarization models are loading or unavailable.",
            )

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty filename.",
            )

        contents = await file.read()
        target_sr = container_instance.config.get("audio", {}).get("sample_rate", 16000)
        try:
            audio = load_audio_bytes(contents, target_sr=target_sr)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid audio format: {e}",
            ) from e

        import time
        t_start = time.perf_counter()

        duration = len(audio) / target_sr
        cfg_buffer = container_instance.config.get("module2_diarization", {}).get("smart_buffer", {})
        frame_size_ms = cfg_buffer.get("chunk_size_ms", 500)
        frame_size = int(target_sr * frame_size_ms / 1000)

        results = []
        current_time = 0.0
        for j in range(0, len(audio), frame_size):
            frame = audio[j:j + frame_size]
            if len(frame) < frame_size:
                frame = np.pad(frame, (0, frame_size - len(frame)))

            res1 = container_instance.module1.process_chunk(frame)
            if res1 and res1["status"] == "PASS":
                res2 = container_instance.module2.process(
                    res1["clean_audio"], res1["t_d"], res1["t_c"]
                )
                chunk_duration = float(len(res1["clean_audio"]) / target_sr)
                start_time = current_time
                end_time = current_time + chunk_duration
                current_time += chunk_duration

                spk_timestamps = []
                for detail in res2.get("speaker_details", []):
                    spk_name = detail.get("speaker")
                    spk_dur = detail.get("speech_duration_sec", chunk_duration)
                    spk_timestamps.append({
                        "speaker": spk_name,
                        "start_time": round(start_time, 3),
                        "end_time": round(start_time + spk_dur, 3),
                        "speech_duration_sec": round(spk_dur, 3)
                    })

                encoded_streams = []
                for stream in res2.get("audio_streams", []):
                    b_io = io.BytesIO()
                    stream_int16 = (stream * 32767).clip(-32768, 32767).astype(np.int16)
                    wavfile.write(b_io, target_sr, stream_int16)
                    encoded_streams.append(base64.b64encode(b_io.getvalue()).decode("ascii"))

                results.append({
                    "chunk_index": len(results),
                    "start_time": round(start_time, 3),
                    "end_time": round(end_time, 3),
                    "branch": res2.get("branch", "BRANCH_A"),
                    "speakers": res2.get("speakers", []),
                    "speaker_timestamps": spk_timestamps,
                    "has_overlap": res2.get("has_overlap", False),
                    "audio_streams_b64": encoded_streams,
                })

        # Flush buffer
        res1 = container_instance.module1.flush()
        if res1 and res1["status"] == "PASS":
            res2 = container_instance.module2.process(
                res1["clean_audio"], res1["t_d"], res1["t_c"]
            )
            chunk_duration = float(len(res1["clean_audio"]) / target_sr)
            start_time = current_time
            end_time = current_time + chunk_duration

            spk_timestamps = []
            for detail in res2.get("speaker_details", []):
                spk_name = detail.get("speaker")
                spk_dur = detail.get("speech_duration_sec", chunk_duration)
                spk_timestamps.append({
                    "speaker": spk_name,
                    "start_time": round(start_time, 3),
                    "end_time": round(start_time + spk_dur, 3),
                    "speech_duration_sec": round(spk_dur, 3)
                })

            encoded_streams = []
            for stream in res2.get("audio_streams", []):
                b_io = io.BytesIO()
                stream_int16 = (stream * 32767).clip(-32768, 32767).astype(np.int16)
                wavfile.write(b_io, target_sr, stream_int16)
                encoded_streams.append(base64.b64encode(b_io.getvalue()).decode("ascii"))

            results.append({
                "chunk_index": len(results),
                "start_time": round(start_time, 3),
                "end_time": round(end_time, 3),
                "branch": res2.get("branch", "BRANCH_A"),
                "speakers": res2.get("speakers", []),
                "speaker_timestamps": spk_timestamps,
                "has_overlap": res2.get("has_overlap", False),
                "audio_streams_b64": encoded_streams,
            })

        proc_time = round(time.perf_counter() - t_start, 3)

        return {
            "status": "success",
            "duration_seconds": round(duration, 2),
            "processing_time_seconds": proc_time,
            "processing_time_ms": round(proc_time * 1000, 2),
            "sample_rate": target_sr,
            "total_segments": len(results),
            "segments": results,
            "chunks": results,
        }

    return app
