"""ASR + Speaker Identification configuration.

Model paths, VAD parameters, runtime provider settings, and speaker
identification thresholds for the realtime ASR pipeline.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from ._base import ConfigBase

# Project root where models/ directory lives
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MODELS_DIR = _PROJECT_ROOT / "models"


class AsrConfig(ConfigBase):
    """Configuration for the ASR + VAD + Speaker Identification engines."""

    model_config = ConfigBase.model_config | {
        "env_prefix": "ASR_",
    }

    model_type: str = Field(
        default="transducer",
        description="ASR model type: 'transducer'",
    )
    language: str = Field(
        default="vi",
        description="Forced language for multilingual ASR models.",
    )

    # Streaming Transducer ASR model paths selected for the far-field pipeline.
    encoder: str = Field(
        default=str(
            _MODELS_DIR
            / "Zipformer-SSL-100h"
            / "encoder-epoch-31-avg-11-chunk-32-left-128.fp16.onnx"
        ),
        description="Path to the transducer encoder model ONNX file.",
    )
    decoder: str = Field(
        default=str(
            _MODELS_DIR
            / "Zipformer-SSL-100h"
            / "decoder-epoch-31-avg-11-chunk-32-left-128.fp16.onnx"
        ),
        description="Path to the transducer decoder model ONNX file.",
    )
    joiner: str = Field(
        default=str(
            _MODELS_DIR
            / "Zipformer-SSL-100h"
            / "joiner-epoch-31-avg-11-chunk-32-left-128.fp16.onnx"
        ),
        description="Path to the transducer joiner model ONNX file.",
    )
    tokens: str = Field(
        default=str(_MODELS_DIR / "Zipformer-SSL-100h" / "tokens.txt"),
        description="Path to the tokens.txt file.",
    )

    # VAD model path
    silero_vad: str = Field(
        default=str(_MODELS_DIR / "silero_vad.onnx"),
        description="Path to the silero_vad.onnx file.",
    )

    # Speaker embedding model path
    speaker_embed: str = Field(
        default=str(_MODELS_DIR / "diarization_models" / "wespeaker_en_voxceleb_resnet34_LM.onnx"),
        description="Path to the speaker embedding ONNX model.",
    )

    # VAD parameters
    vad_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="VAD threshold (0.0 to 1.0) for speech detection.",
    )
    min_silence_duration: float = Field(
        default=0.25,
        gt=0.0,
        description="Minimum duration of silence in seconds to trigger end-of-utterance.",
    )
    min_speech_duration: float = Field(
        default=0.50,
        gt=0.0,
        description="Minimum duration of speech in seconds to register utterance.",
    )
    max_speech_duration: float = Field(
        default=5.0,
        gt=0.0,
        description="Maximum duration of a single speech segment in seconds.",
    )

    # Runtime parameters
    num_threads: int = Field(
        default=4,
        ge=1,
        description="Number of threads for ASR network computation.",
    )
    provider: str = Field(
        default="cuda",
        description="Execution provider for ASR model ('cpu' or 'cuda').",
    )
    emit_partials: bool = Field(
        default=False,
        description="Whether to emit speculative partial transcripts.",
    )
    audio_retention_hours: int = Field(
        default=24,
        ge=1,
        le=24 * 30,
        description="Default local retention time for recoverable meeting recordings.",
    )
    accuracy_mode: bool = Field(
        default=True,
        description="Require the full far-field enhancement pipeline at startup.",
    )
    preprocessing_chunk_seconds: float = Field(default=2.5, gt=0.0)
    preprocessing_overlap_seconds: float = Field(default=0.3, ge=0.0)
    denoiser_atten_lim_db: float = Field(default=15.0, gt=0.0)
    denoiser_post_filter: bool = Field(default=False)

    # Speaker identification
    speaker_similarity_threshold: float = Field(
        default=0.88,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for speaker matching.",
    )
