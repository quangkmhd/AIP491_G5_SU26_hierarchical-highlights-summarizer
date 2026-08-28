"""Central Pipeline Orchestrator Service.

Coordinates sd-module (Diarization) -> asr-module (Speech-to-Text) -> llms-module (Summarization)
for both audio file upload batch processing and real-time audio chunk streaming.
"""
import logging
import time
from typing import Any, Callable, Optional
import asyncio
import httpx
from backend.db.database import DatabaseManager
from backend.services.audio_router import AudioStreamRouter
import os
from pathlib import Path
from backend.services.meeting_stream_manager import MeetingStreamManager

logger = logging.getLogger(__name__)


def _load_backend_env_config() -> dict[str, int]:
    """Load MIN_UTTERANCES_STACK and UTTERANCES_OVERLAP_CONTEXT from backend/.env or env vars."""
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"
    config = {
        "min_utterances_stack": 40,
        "overlap_context": 30,
    }

    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k_clean = k.strip()
                        if k_clean == "MIN_UTTERANCES_STACK":
                            config["min_utterances_stack"] = int(v.strip())
                        elif k_clean == "UTTERANCES_OVERLAP_CONTEXT":
                            config["overlap_context"] = int(v.strip())
        except Exception as e:
            logger.warning(f"Failed to read {env_file}: {e}")

    # Fallback to environment variables if present
    if "MIN_UTTERANCES_STACK" in os.environ:
        try:
            config["min_utterances_stack"] = int(os.environ["MIN_UTTERANCES_STACK"])
        except ValueError:
            pass

    if "UTTERANCES_OVERLAP_CONTEXT" in os.environ:
        try:
            config["overlap_context"] = int(os.environ["UTTERANCES_OVERLAP_CONTEXT"])
        except ValueError:
            pass

    return config


class PipelineOrchestrator:
    """Master pipeline orchestrator connecting all AI microservices and persistent SQLite DB."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        sd_url: str = "http://localhost:8002/api/v1/diarize",
        asr_url: str = "http://localhost:8000/api/v1/transcribe",
        llm_url: str = "http://localhost:8003/api/v1/meetings/process",
        min_utterances_stack: Optional[int] = None,
        overlap_context: Optional[int] = None,
        stream_manager: MeetingStreamManager | None = None,
    ):
        self.db = db_manager
        self.sd_url = sd_url
        self.asr_url = asr_url
        self.llm_url = llm_url

        env_cfg = _load_backend_env_config()
        self.min_utterances_stack = (
            min_utterances_stack
            if min_utterances_stack is not None
            else env_cfg["min_utterances_stack"]
        )
        self.overlap_context = (
            overlap_context
            if overlap_context is not None
            else env_cfg["overlap_context"]
        )

        # Tracks the count of summarized utterances per session to support periodic intervals
        self._last_summarized_count: dict[str, int] = {}
        self.router = AudioStreamRouter(asr_url=asr_url)
        self.stream_manager = stream_manager
        self._live_session_locks: dict[str, asyncio.Lock] = {}

    async def process_live_audio_chunk(
        self,
        session_id: str,
        audio_bytes: bytes,
        filename: str = "live_chunk.wav",
        progress_callback: Optional[Callable[[dict[str, Any]], Any]] = None,
    ) -> dict[str, Any]:
        """Process one live audio chunk and publish each ASR utterance immediately."""
        if self.stream_manager is None:
            raise RuntimeError("Live streaming requires a MeetingStreamManager")
        lock = self._live_session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            return await self.process_audio_file(
                session_id=session_id,
                audio_bytes=audio_bytes,
                filename=filename,
                progress_callback=progress_callback,
                _stream_live=True,
            )

    async def reset_diarization_session(self) -> None:
        """Calls the reset endpoint on the sd-module to clear previous voiceprints and buffers."""
        reset_url = self.sd_url.replace("/diarize", "/reset")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(reset_url)
                logger.info(f"Successfully reset sd-module state at {reset_url}")
        except Exception as e:
            logger.warning(f"Failed to reset sd-module state: {e}")

    async def process_audio_file(
        self,
        session_id: str,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        is_final: bool = False,
        progress_callback: Optional[Callable[[dict[str, Any]], Any]] = None,
        _stream_live: bool = False,
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
            # Stage 1: Diarization & Speaker Separation (sd-module)
            if not _stream_live:
                self.db.update_session_status(session_id, "diarizing", 10.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "diarizing",
                    "progress_percentage": 10.0,
                })

            async with httpx.AsyncClient(timeout=180.0) as client:
                files = {"file": (filename, audio_bytes, "audio/wav")}
                params = {"is_final": "true" if is_final else "false"}
                resp_sd = await client.post(self.sd_url, files=files, params=params)
                if resp_sd.status_code != 200:
                    raise RuntimeError(f"sd-module failed HTTP {resp_sd.status_code}: {resp_sd.text}")

                sd_json = resp_sd.json()

            segments = sd_json.get("segments", [])
            logger.info(f"Session {session_id}: Diarization returned {len(segments)} segments.")

            if not _stream_live:
                self.db.update_session_status(session_id, "diarizing", 30.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "diarizing",
                    "progress_percentage": 30.0,
                })

            # Stage 2: Transcribe via Parallel Async STT (asr-module)
            if not _stream_live:
                self.db.update_session_status(session_id, "transcribing", 40.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "transcribing",
                    "progress_percentage": 40.0,
                })

            existing_utts = self.db.get_utterances(session_id)
            u_index = len(existing_utts)
            time_offset = round(max((float(u.get("end_time") or 0.0) for u in existing_utts), default=0.0), 2)

            db_utterances = []
            total_segs = max(1, len(segments))

            for seg_idx, seg in enumerate(segments):
                routed_utts = await self.router.route_diarized_segment(seg)
                for item in routed_utts:
                    rec = self.db.add_utterance(
                        session_id=session_id,
                        speaker_id=item["speaker_id"],
                        text=item["text"],
                        utterance_index=u_index,
                        start_time=round(time_offset + float(item.get("start_time") or 0.0), 2),
                        end_time=round(time_offset + float(item.get("end_time") or 0.0), 2),
                        has_overlap=item["has_overlap"],
                    )
                    db_utterances.append(rec)
                    u_index += 1

                    if _stream_live:
                        await self.stream_manager.publish(
                            session_id, rec, progress_callback=progress_callback
                        )

                    if progress_callback:
                        await progress_callback({
                            "type": "utterance-emitted",
                            "session_id": session_id,
                            "utterance": rec,
                        })

                current_progress = 40.0 + (30.0 * (seg_idx + 1) / total_segs)
                if not _stream_live:
                    self.db.update_session_status(
                        session_id, "transcribing", round(current_progress, 1)
                    )

            if not _stream_live:
                self.db.update_session_status(session_id, "transcribing", 70.0)
            logger.info(f"Session {session_id}: Transcribed {len(db_utterances)} utterances.")

            if _stream_live:
                return {
                    "session_id": session_id,
                    "status": "recording",
                    "new_utterances": len(db_utterances),
                    "total_utterances": len(self.db.get_utterances(session_id)),
                    "processing_time_ms": int((time.time() - start_time) * 1000),
                }

            # If no utterances were transcribed in this audio frame (silence), complete gracefully
            if not db_utterances and not is_final:
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.db.update_session_status(session_id, "completed", 100.0)
                existing_summary_rec = self.db.get_summary(session_id)
                current_summary = existing_summary_rec.get("hierarchical_json") if existing_summary_rec else None
                result = {
                    "session_id": session_id,
                    "status": "completed",
                    "total_utterances": len(existing_utts),
                    "processing_time_ms": elapsed_ms,
                }
                if current_summary:
                    result["summary"] = current_summary

                if progress_callback:
                    await progress_callback({
                        "type": "session-completed",
                        "session_id": session_id,
                        "result": result,
                    })
                logger.info(f"Session {session_id}: Completed with 0 new utterances in {elapsed_ms}ms.")
                return result

            # Stage 3: Periodic LLM Topic Segmentation & Hierarchical Summarization
            all_session_utts = self.db.get_utterances(session_id)
            total_session_utts = len(all_session_utts)
            last_summarized_count = self._last_summarized_count.get(session_id, 0)
            new_utts_since_last_summary = total_session_utts - last_summarized_count

            # Determine required new utterances threshold:
            # - Initial summary run: requires min_utterances_stack (e.g., 40)
            # - Subsequent periodic runs: requires stride = (min_utterances_stack - overlap_context) (e.g., 40 - 30 = 10)
            required_step = (
                self.min_utterances_stack
                if last_summarized_count == 0
                else max(1, self.min_utterances_stack - self.overlap_context)
            )

            # Check if periodic stack threshold is reached or if this is the final flush
            if new_utts_since_last_summary < required_step and not is_final:
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.db.update_session_status(session_id, "completed", 100.0)
                logger.info(
                    f"[LLM-Stack] Session {session_id}: Stacked {new_utts_since_last_summary}/{required_step} "
                    f"new utterances (Total in DB: {total_session_utts}, Last summarized: {last_summarized_count}). "
                    f"Waiting for next periodic interval."
                )
                existing_summary_rec = self.db.get_summary(session_id)
                current_summary = existing_summary_rec.get("hierarchical_json") if existing_summary_rec else None
                result = {
                    "session_id": session_id,
                    "status": "completed",
                    "total_utterances": total_session_utts,
                    "processing_time_ms": elapsed_ms,
                }
                if current_summary:
                    result["summary"] = current_summary

                if progress_callback:
                    await progress_callback({
                        "type": "session-completed",
                        "session_id": session_id,
                        "result": result,
                    })
                return result

            if total_session_utts == 0:
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.db.update_session_status(session_id, "completed", 100.0)
                logger.info(f"[LLM-Stack] Session {session_id}: 0 utterances in DB, skipping LLM call.")
                return {
                    "session_id": session_id,
                    "status": "completed",
                    "total_utterances": 0,
                    "processing_time_ms": elapsed_ms,
                }

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

            # Window slicing: Slice the last `min_utterances_stack` utterances (e.g. 40)
            # which naturally contains 30 overlap old utterances + 10 new utterances
            start_window_idx = max(0, total_session_utts - self.min_utterances_stack)
            utts_to_summarize = all_session_utts[start_window_idx:total_session_utts]
            overlap_count = max(0, len(utts_to_summarize) - new_utts_since_last_summary)

            logger.info(
                f"[LLM-Trigger] Session {session_id}: Triggering LLM summarization on window "
                f"[{start_window_idx}:{total_session_utts}] ({len(utts_to_summarize)} utterances = "
                f"{new_utts_since_last_summary} new + {overlap_count} overlap). Stride={required_step}."
            )

            llm_payload = {
                "meeting_title": title,
                "language": "vi",
                "utterances": [
                    {
                        "speaker": u["speaker_id"],
                        "text": u["text"],
                        "index": u["utterance_index"],
                    }
                    for u in utts_to_summarize
                ],
            }

            async with httpx.AsyncClient(timeout=300.0) as client:
                resp_llm = await client.post(self.llm_url, json=llm_payload)
                if resp_llm.status_code != 200:
                    raise RuntimeError(f"llms-module failed HTTP {resp_llm.status_code}: {resp_llm.text}")

                resp_json = resp_llm.json()
                summary_json = resp_json.get("summary", resp_json)

            # Record that we have summarized up to the current total count
            self._last_summarized_count[session_id] = total_session_utts

            elapsed_ms = int((time.time() - start_time) * 1000)
            self.db.save_summary(session_id, summary_json, processing_time_ms=elapsed_ms)
            self.db.update_session_status(session_id, "completed", 100.0)

            total_chapters = len(summary_json.get("segments", []))
            logger.info(
                f"[LLM-Trigger] Session {session_id}: Summarized {len(utts_to_summarize)} utterances "
                f"into {total_chapters} topic chapters successfully in {elapsed_ms}ms."
            )

            result = {
                "session_id": session_id,
                "status": "completed",
                "total_utterances": total_session_utts,
                "summary": summary_json,
                "processing_time_ms": elapsed_ms,
            }

            if progress_callback:
                await progress_callback({
                    "type": "session-completed",
                    "session_id": session_id,
                    "result": result,
                })

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

    async def finalize_live_session(
        self,
        session_id: str,
        progress_callback: Optional[Callable[[dict[str, Any]], Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Flush trailing audio, publish its utterances, then flush the LLM stream."""
        if self.stream_manager is None:
            raise RuntimeError("Live streaming requires a MeetingStreamManager")
        lock = self._live_session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            flush_url = self.sd_url.rsplit("/", 1)[0] + "/flush"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(flush_url)
            if response.status_code != 200:
                raise RuntimeError(
                    f"sd-module flush failed HTTP {response.status_code}: {response.text}"
                )

            existing_utts = self.db.get_utterances(session_id)
            utterance_index = len(existing_utts)
            time_offset = round(
                max((float(u.get("end_time") or 0.0) for u in existing_utts), default=0.0),
                2,
            )
            for segment in response.json().get("segments", []):
                for item in await self.router.route_diarized_segment(segment):
                    record = self.db.add_utterance(
                        session_id=session_id,
                        speaker_id=item["speaker_id"],
                        text=item["text"],
                        utterance_index=utterance_index,
                        start_time=round(time_offset + float(item.get("start_time") or 0.0), 2),
                        end_time=round(time_offset + float(item.get("end_time") or 0.0), 2),
                        has_overlap=item["has_overlap"],
                    )
                    utterance_index += 1
                    await self.stream_manager.publish(
                        session_id, record, progress_callback=progress_callback
                    )
                    if progress_callback:
                        await progress_callback({
                            "type": "utterance-emitted",
                            "session_id": session_id,
                            "utterance": record,
                        })

            return await self.stream_manager.finish(
                session_id, progress_callback=progress_callback
            )
