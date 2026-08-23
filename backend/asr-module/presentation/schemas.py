"""API Request & Response Schemas (DTOs)."""

from typing import Optional
from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    filename: Optional[str] = Field(None, description="Original name of uploaded audio file")
    text: str = Field(..., description="Recognized speech transcript")
    duration_seconds: float = Field(..., description="Duration of audio in seconds")
    sample_rate: int = Field(..., description="Sample rate of audio processed")
    processing_time_ms: Optional[int] = Field(None, description="Total server processing time in milliseconds")
    processing_time_seconds: Optional[float] = Field(None, description="Total server processing time in seconds")
    status: str = Field("success", description="Status of recognition request")


class HealthCheckResponse(BaseModel):
    status: str
    app: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
