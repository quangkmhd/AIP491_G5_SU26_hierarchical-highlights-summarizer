"""Configuration settings module using Pydantic Settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "VietASR Hosting Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Model Artifacts Config
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    MODEL_ENCODER_PATH: str = str(BASE_DIR / "models" / "encoder.onnx")
    MODEL_DECODER_PATH: str = str(BASE_DIR / "models" / "decoder.onnx")
    MODEL_JOINER_PATH: str = str(BASE_DIR / "models" / "joiner.onnx")
    TOKENS_PATH: str = str(BASE_DIR / "models" / "tokens.txt")
    
    # Inference Config
    NUM_THREADS: int = 4
    DECODING_METHOD: str = "greedy_search"  # Options: greedy_search, modified_beam_search
    SAMPLE_RATE: int = 16000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
