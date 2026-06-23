import asyncio
import json
import threading
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIST_DIR
from app.schemas import SummaryRequest, SummaryResponse
from app.services.recap_service import RecapService


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIP491 Meeting Recap Studio",
        version="0.1.0",
        description="FastAPI service for DR1 Highlights and DR2 Hierarchical meeting recap methods.",
    )
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        built_index = FRONTEND_DIST_DIR / "index.html"
        if built_index.exists():
            return FileResponse(built_index)
        raise HTTPException(
            status_code=503,
            detail="React frontend has not been built. Run `npm install` and `npm run build` in tools/09-meeting-recap-webapp/frontend.",
        )

    @app.post("/api/summarize", response_model=SummaryResponse, tags=["summary"])
    def summarize(request: SummaryRequest) -> dict:
        service = RecapService()
        try:
            return service.summarize(
                request.transcript,
                method=request.method,
                input_name=request.input_name,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/summarize/stream", tags=["summary"])
    async def summarize_stream(request: SummaryRequest) -> StreamingResponse:
        service = RecapService()

        async def events() -> AsyncIterator[str]:
            queue: asyncio.Queue[dict | None] = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def run_summary() -> None:
                try:
                    for event in service.summarize_stream(
                        request.transcript,
                        method=request.method,
                        input_name=request.input_name,
                    ):
                        asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()
                finally:
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

            threading.Thread(target=run_summary, name="summary-stream-worker", daemon=True).start()

            while True:
                event = await queue.get()
                if event is None:
                    break
                yield json.dumps(event, ensure_ascii=False) + "\n"
                await asyncio.sleep(0)

        return StreamingResponse(
            events(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app


app = create_app()
