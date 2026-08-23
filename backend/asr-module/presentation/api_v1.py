"""API Router v1."""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from config import settings
from domain.interfaces import ASRModelInterface
from application.transcribe_service import TranscribeAudioUseCase
from presentation.schemas import TranscribeResponse, HealthCheckResponse, ErrorResponse
from infrastructure.logger import logger

router = APIRouter()

# Dependency container for ASR model driver (set at app startup)
_asr_driver_instance: ASRModelInterface = None


def set_asr_driver(driver: ASRModelInterface):
    global _asr_driver_instance
    _asr_driver_instance = driver


def get_transcribe_use_case() -> TranscribeAudioUseCase:
    if _asr_driver_instance is None or not _asr_driver_instance.is_ready():
        raise HTTPException(status_code=503, detail="ASR Model service is not ready yet.")
    return TranscribeAudioUseCase(model_driver=_asr_driver_instance)


@router.get("/healthz", response_model=HealthCheckResponse, tags=["Health"])
async def healthz():
    """Liveness probe endpoint."""
    return HealthCheckResponse(
        status="alive",
        app=settings.APP_NAME,
        version=settings.APP_VERSION
    )


@router.get("/readyz", response_model=HealthCheckResponse, tags=["Health"])
async def readyz():
    """Readiness probe endpoint."""
    if _asr_driver_instance is None or not _asr_driver_instance.is_ready():
        raise HTTPException(status_code=503, detail="ASR Model is loading or unavailable.")
    return HealthCheckResponse(
        status="ready",
        app=settings.APP_NAME,
        version=settings.APP_VERSION
    )


@router.post(
    "/api/v1/transcribe",
    response_model=TranscribeResponse,
    responses={500: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    tags=["ASR"]
)
async def transcribe(
    file: UploadFile = File(...),
    use_case: TranscribeAudioUseCase = Depends(get_transcribe_use_case)
):
    """Transcribe uploaded audio file (.wav, .mp3, .flac)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        result = use_case.execute(audio_bytes=audio_bytes, filename=file.filename)
        return TranscribeResponse(
            filename=result.filename,
            text=result.text,
            duration_seconds=result.duration_seconds,
            sample_rate=result.sample_rate,
            processing_time_ms=result.processing_time_ms,
            processing_time_seconds=result.processing_time_seconds,
            status=result.status
        )
    except ValueError as ve:
        logger.warning(f"Bad request for file '{file.filename}': {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal server error during transcription of '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
