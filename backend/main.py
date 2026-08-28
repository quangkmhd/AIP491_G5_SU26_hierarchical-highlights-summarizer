"""Central Backend Orchestrator & Gateway Entrypoint."""

from contextlib import asynccontextmanager
import logging
import os
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import sessions_router, ws_router
from backend.db.database import DatabaseManager
from backend.services.meeting_stream_manager import MeetingStreamManager
from backend.services.pipeline_orchestrator import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("backend.gateway")


def service_urls_from_env() -> dict[str, str]:
    """Resolve microservice endpoints for local runs and container deployments."""
    return {
        "sd_url": os.getenv("SD_URL", "http://localhost:8002/api/v1/diarize"),
        "asr_url": os.getenv("ASR_URL", "http://localhost:8000/api/v1/transcribe"),
        "llm_url": os.getenv("LLM_URL", "http://localhost:8003/api/v1/meetings/process"),
        "llm_ws_url": os.getenv("LLM_WS_URL", "ws://localhost:8003/ws"),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and central pipeline orchestrator on server startup."""
    logger.info("Initializing Backend Central Gateway (Port 8080)...")
    db_manager = DatabaseManager()
    urls = service_urls_from_env()
    stream_manager = MeetingStreamManager(
        db_manager=db_manager,
        ws_url=urls["llm_ws_url"],
    )
    orchestrator = PipelineOrchestrator(
        db_manager=db_manager,
        stream_manager=stream_manager,
        sd_url=urls["sd_url"],
        asr_url=urls["asr_url"],
        llm_url=urls["llm_url"],
    )

    app.state.db = db_manager
    app.state.orchestrator = orchestrator

    logger.info("Backend Gateway initialized successfully.")
    yield
    await stream_manager.close_all()
    logger.info("Shutting down Backend Gateway.")


def create_app() -> FastAPI:
    """FastAPI Application Factory for backend orchestrator."""
    app = FastAPI(
        title="Central Pipeline Orchestrator & Gateway",
        version="1.0.0",
        description="Gateway microservice orchestrating sd-module, asr-module, and llms-module pipelines.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions_router)
    app.include_router(ws_router)

    @app.get("/health")
    @app.get("/healthz")
    def health_check() -> dict[str, Any]:
        """Health probe checking gateway readiness and DB connectivity."""
        db_ok = False
        try:
            conn = app.state.db.get_connection()
            conn.execute("SELECT 1;")
            db_ok = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        is_healthy = db_ok and hasattr(app.state, "orchestrator")
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "Central Backend Orchestrator & Gateway",
            "database_connected": db_ok,
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True)
