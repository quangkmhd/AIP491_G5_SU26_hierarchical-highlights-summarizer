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
        default="qwen3",
        description="ASR model type: 'transducer' or 'qwen3'",
    )
    language: str = Field(
        default="vi",
        description="Forced language for multilingual ASR models (e.g. 'vi' for Qwen3).",
    )

    # Transducer ASR model paths
    encoder: str = Field(
        default=str(_MODELS_DIR / "Zipformer-30M-RNNT-6000h" / "encoder-epoch-20-avg-10.int8.onnx"),
        description="Path to the transducer encoder model ONNX file.",
    )
    decoder: str = Field(
        default=str(_MODELS_DIR / "Zipformer-30M-RNNT-6000h" / "decoder-epoch-20-avg-10.int8.onnx"),
        description="Path to the transducer decoder model ONNX file.",
    )
    joiner: str = Field(
        default=str(_MODELS_DIR / "Zipformer-30M-RNNT-6000h" / "joiner-epoch-20-avg-10.int8.onnx"),
        description="Path to the transducer joiner model ONNX file.",
    )
    tokens: str = Field(
        default=str(_MODELS_DIR / "Zipformer-30M-RNNT-6000h" / "tokens.txt"),
        description="Path to the tokens.txt file.",
    )

    # Qwen3 model paths
    qwen3_conv_frontend: str = Field(
        default=str(_MODELS_DIR / "sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25" / "conv_frontend.onnx"),
        description="Path to conv_frontend.onnx for Qwen3 ASR.",
    )
    qwen3_encoder: str = Field(
        default=str(_MODELS_DIR / "sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25" / "encoder.int8.onnx"),
        description="Path to encoder.int8.onnx for Qwen3 ASR.",
    )
    qwen3_decoder: str = Field(
        default=str(_MODELS_DIR / "sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25" / "decoder.int8.onnx"),
        description="Path to decoder.int8.onnx for Qwen3 ASR.",
    )
    qwen3_tokenizer: str = Field(
        default=str(_MODELS_DIR / "sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25" / "tokenizer"),
        description="Path to tokenizer directory for Qwen3 ASR.",
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
        default=0.5,
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

    # Speaker identification
    speaker_similarity_threshold: float = Field(
        default=0.88,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for speaker matching.",
    )
