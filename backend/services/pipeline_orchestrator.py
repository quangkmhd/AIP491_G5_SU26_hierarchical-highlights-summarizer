"""Central Pipeline Orchestrator Service.

Coordinates sd-module (Diarization) -> asr-module (Speech-to-Text) -> llms-module (Summarization)
for both audio file upload batch processing and real-time audio chunk streaming.
"""
import logging
import time
from typing import Any, Callable, Optional
import httpx
from backend.db.database import DatabaseManager
from backend.services.audio_router import AudioStreamRouter
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_backend_env_config() -> dict[str, int]:
    """Load MIN_UTTERANCES_STACK and UTTERANCES_OVERLAP_CONTEXT from backend/.env or env vars."""
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"
    config = {
        "min_utterances_stack": 40,
        "overlap_context": 5,
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

    async def process_audio_file(
        self,
        session_id: str,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        is_final: bool = False,
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
            # Stage 1: Diarization & Speaker Separation (sd-module)
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
                resp_sd = await client.post(self.sd_url, files=files)
                if resp_sd.status_code != 200:
                    raise RuntimeError(f"sd-module failed HTTP {resp_sd.status_code}: {resp_sd.text}")

                sd_json = resp_sd.json()

            segments = sd_json.get("segments", [])
            logger.info(f"Session {session_id}: Diarization returned {len(segments)} segments.")

            self.db.update_session_status(session_id, "diarizing", 30.0)
            if progress_callback:
                await progress_callback({
                    "type": "progress",
                    "session_id": session_id,
                    "status": "diarizing",
                    "progress_percentage": 30.0,
                })

            # Stage 2: Transcribe via Parallel Async STT (asr-module)
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

            # If no utterances were transcribed in this audio frame (silence), complete gracefully
            if not db_utterances and not is_final:
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.db.update_session_status(session_id, "completed", 100.0)
                result = {
                    "session_id": session_id,
                    "status": "completed",
                    "total_utterances": len(existing_utts),
                    "summary": self.db.get_summary(session_id) or {"segments": []},
                    "processing_time_ms": elapsed_ms,
                }
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

            # Check if periodic stack threshold is reached or if this is the final flush
            if new_utts_since_last_summary < self.min_utterances_stack and not is_final:
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.db.update_session_status(session_id, "completed", 100.0)
                logger.info(
                    f"Session {session_id}: Stacked {new_utts_since_last_summary}/{self.min_utterances_stack} "
                    f"new utterances (Total: {total_session_utts}). Waiting for next periodic interval."
                )
                result = {
                    "session_id": session_id,
                    "status": "completed",
                    "total_utterances": total_session_utts,
                    "summary": self.db.get_summary(session_id) or {"segments": []},
                    "processing_time_ms": elapsed_ms,
                }
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
                return {
                    "session_id": session_id,
                    "status": "completed",
                    "total_utterances": 0,
                    "summary": {"segments": []},
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

            # Gather utterances incorporating the configured overlap context from previous interval
            if self.overlap_context > 0 and last_summarized_count > 0:
                start_context_idx = max(0, last_summarized_count - self.overlap_context)
                utts_to_summarize = all_session_utts[start_context_idx:]
                logger.info(
                    f"Session {session_id}: Running periodic LLM summarization on {len(utts_to_summarize)} utterances "
                    f"({new_utts_since_last_summary} new + {len(utts_to_summarize) - new_utts_since_last_summary} overlap context)."
                )
            else:
                utts_to_summarize = all_session_utts
                logger.info(
                    f"Session {session_id}: Running initial LLM summarization on {len(utts_to_summarize)} utterances."
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

                summary_json = resp_llm.json()

            # Record that we have summarized up to the current total count
            self._last_summarized_count[session_id] = total_session_utts

            elapsed_ms = int((time.time() - start_time) * 1000)
            self.db.save_summary(session_id, summary_json, processing_time_ms=elapsed_ms)
            self.db.update_session_status(session_id, "completed", 100.0)

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

            logger.info(f"Session {session_id}: Summarized {total_session_utts} utterances successfully in {elapsed_ms}ms.")
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

    async def trigger_final_summary(
        self,
        session_id: str,
        progress_callback: Optional[Callable[[dict[str, Any]], Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Force a final LLM summarization flush across all session utterances when recording finishes."""
        all_session_utts = self.db.get_utterances(session_id)
        if not all_session_utts:
            return None

        last_summarized_count = self._last_summarized_count.get(session_id, 0)
        total_session_utts = len(all_session_utts)

        # If already summarized up to latest utterance, return current summary
        if total_session_utts == last_summarized_count:
            return self.db.get_summary(session_id)

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
                for u in all_session_utts
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp_llm = await client.post(self.llm_url, json=llm_payload)
                if resp_llm.status_code == 200:
                    summary_json = resp_llm.json()
                    self.db.save_summary(session_id, summary_json)
                    self._last_summarized_count[session_id] = total_session_utts

                    if progress_callback:
                        await progress_callback({
                            "type": "session-completed",
                            "session_id": session_id,
                            "result": {
                                "session_id": session_id,
                                "status": "completed",
                                "total_utterances": total_session_utts,
                                "summary": summary_json,
                            },
                        })
                    return summary_json
        except Exception as e:
            logger.warning(f"Final summary flush failed for session {session_id}: {e}")

        return self.db.get_summary(session_id)
