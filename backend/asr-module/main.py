"""Main entrypoint for ASR Service."""

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from config import settings
from infrastructure.logger import logger
from infrastructure.sherpa_onnx_driver import SherpaOnnxASRDriver
from presentation.api_v1 import router, set_asr_driver


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load Sherpa-ONNX model
    logger.info(f"Starting {settings.APP_NAME} (v{settings.APP_VERSION})...")
    driver = SherpaOnnxASRDriver()
    set_asr_driver(driver)
    logger.info("Application startup complete and ready to serve requests.")
    yield
    # Shutdown
    logger.info("Shutting down ASR service...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Clean Architecture ASR Speech-to-Text Microservice powered by Sherpa-ONNX",
    lifespan=lifespan
)

# Include API v1 Router
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
