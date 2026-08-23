"""Central Pipeline Orchestrator Service.

Coordinates sd-module (Diarization) -> asr-module (Speech-to-Text) -> llms-module (Summarization)
for both audio file upload batch processing and real-time audio chunk streaming.
"""

import asyncio
import io
import logging
import time
from typing import Any, Callable, Optional
import httpx
import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal
import soundfile as sf

from backend.db.database import DatabaseManager
from backend.services.audio_router import AudioStreamRouter, ndarray_to_wav_bytes

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Master pipeline orchestrator connecting all AI microservices and persistent SQLite DB."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        sd_url: str = "http://localhost:8002/api/v1/diarize",
        asr_url: str = "http://localhost:8001/api/v1/transcribe",
        llm_url: str = "http://localhost:8000/api/v1/meetings/process",
    ):
        self.db = db_manager
        self.sd_url = sd_url
        self.asr_url = asr_url
        self.llm_url = llm_url
        self.router = AudioStreamRouter(asr_url=asr_url)

    async def process_audio_file(
        self,
        session_id: str,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        progress_callback: Optional[Callable[[dict[str, Any]], Any]] = None,
    ) -> dict[str, Any]:
        """
        Execute full 3-stage pipeline for batch audio file upload:
        Stage 1: Diarize & Separate (sd-module) [30%]
        Stage 2: Transcribe via Parallel Async STT (asr-module) [70%]
        Stage 3: Multiscale TextTiling & LLM Summarize (llms-module) [100%]
        """
        start_time = time.time()
        logger.info(f"Starting pipeline processing for session {session_id} ({filename})")

        try:
            # -------------------------------------------------------------
            # Stage 1: Diarization & Speaker Separation (sd-module)
            # -------------------------------------------------------------
            self.db.update_session_status(session_id, "diarizing", 10.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "diarizing",
                    "progress_percentage": 10.0,
                })

            async with httpx.AsyncClient(timeout=300.0) as client:
                files = {"file": (filename, audio_bytes, "audio/wav")}
                resp_sd = await client.post(self.sd_url, files=files)
                if resp_sd.status_code != 200:
                    raise RuntimeError(f"sd-module failed HTTP {resp_sd.status_code}: {resp_sd.text}")

                sd_data = resp_sd.json()

            segments = sd_data.get("segments", [])
            logger.info(f"Session {session_id}: Diarization returned {len(segments)} segments.")
            self.db.update_session_status(session_id, "diarizing", 30.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "diarizing",
                    "progress_percentage": 30.0,
                })

            # -------------------------------------------------------------
            # Stage 2: Transcribe via Parallel Async STT (asr-module)
            # -------------------------------------------------------------
            self.db.update_session_status(session_id, "transcribing", 40.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "transcribing",
                    "progress_percentage": 40.0,
                })

            db_utterances = []
            u_index = 0
            total_segs = max(1, len(segments))

            for seg_idx, seg in enumerate(segments):
                routed_utts = await self.router.route_segment_to_asr(seg)
                for item in routed_utts:
                    rec = self.db.add_utterance(
                        session_id=session_id,
                        speaker_id=item["speaker_id"],
                        text=item["text"],
                        utterance_index=u_index,
                        start_time=item["start_time"],
                        end_time=item["end_time"],
                        has_overlap=item["has_overlap"],
                    )
                    db_utterances.append(rec)
                    u_index += 1

                    if progress_callback:
                        await progress_callback({
                            "type": "utterance-emitted",
                            "session_id": session_id,
                            "utterance": rec,
                        })

                current_progress = 40.0 + (30.0 * (seg_idx + 1) / total_segs)
                self.db.update_session_status(session_id, "transcribing", round(current_progress, 1))

            self.db.update_session_status(session_id, "transcribing", 70.0)
            logger.info(f"Session {session_id}: Transcribed {len(db_utterances)} utterances.")

            # -------------------------------------------------------------
            # Stage 3: LLM Topic Segmentation & Hierarchical Summarization (llms-module)
            # -------------------------------------------------------------
            self.db.update_session_status(session_id, "summarizing", 75.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "summarizing",
                    "progress_percentage": 75.0,
                })

            session_record = self.db.get_session(session_id)
            title = session_record.get("title") if session_record else "Meeting Summary"

            llm_payload = {
                "meeting_title": title,
                "language": "vi",
                "utterances": [
                    {
                        "speaker": u["speaker_id"],
                        "text": u["text"],
                        "index": u["utterance_index"],
                    }
                    for u in db_utterances
                ],
            }

            async with httpx.AsyncClient(timeout=300.0) as client:
                resp_llm = await client.post(self.llm_url, json=llm_payload)
                if resp_llm.status_code != 200:
                    raise RuntimeError(f"llms-module failed HTTP {resp_llm.status_code}: {resp_llm.text}")

                summary_json = resp_llm.json()

            elapsed_ms = int((time.time() - start_time) * 1000)
            self.db.save_summary(session_id, summary_json, processing_time_ms=elapsed_ms)
            self.db.update_session_status(session_id, "completed", 100.0)

            result = {
                "session_id": session_id,
                "status": "completed",
                "total_utterances": len(db_utterances),
                "summary": summary_json,
                "processing_time_ms": elapsed_ms,
            }

            if progress_callback:
                await progress_callback({
                    "type": "session-completed",
                    "session_id": session_id,
                    "result": result,
                })

            logger.info(f"Session {session_id}: Completed successfully in {elapsed_ms}ms.")
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Pipeline processing failed for session {session_id}: {error_msg}")
            self.db.fail_session(session_id, error_msg)
            if progress_callback:
                await progress_callback({
                    "type": "session-failed",
                    "session_id": session_id,
                    "error": error_msg,
                })
            raise
