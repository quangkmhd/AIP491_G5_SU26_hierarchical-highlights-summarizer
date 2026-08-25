"""
Deferred Segment Buffer (DSR — Deferred Segment Recycling)
In-memory buffer that stores UNKNOWN segments for later reconciliation
when the VoiceprintPool is updated with new profiles.
"""

import time
import logging
import numpy as np
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeferredSegment:
    """Represents a single deferred audio segment awaiting reconciliation."""
    embedding: np.ndarray       # 512-dim CAM++ embedding (already extracted)
    audio: np.ndarray           # Clean audio (already denoised)
    t_d: float                  # Speech duration (from VAD)
    t_c: float                  # VAD confidence
    origin: str                 # "BRANCH_A" | "OVERLAP_STREAM"
    created_at: float           # time.time() at push
    retry_count: int = 0        # Number of reconcile attempts


class DeferredSegmentBuffer:
    """
    In-memory buffer for UNKNOWN segments that may be re-identified
    once the VoiceprintPool acquires new speaker profiles.

    Eviction policy (applied on every push):
      1. Remove expired segments (age > max_age_seconds)
      2. Remove over-retried segments (retry_count >= max_retries)
      3. FIFO eviction if capacity is exceeded
    """

    def __init__(self, config: dict):
        cfg = config.get("module2_diarization", {}).get("deferred_buffer", {})
        self.enabled: bool = cfg.get("enabled", True)
        self.max_segments: int = cfg.get("max_segments", 50)
        self.max_age_seconds: float = cfg.get("max_age_seconds", 120.0)
        self.max_retries: int = cfg.get("max_retries", 5)
        self.segments: list[DeferredSegment] = []

        logger.info(
            f"[DeferredBuffer] Initialized — enabled={self.enabled}, "
            f"capacity={self.max_segments}, TTL={self.max_age_seconds}s, "
            f"max_retries={self.max_retries}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, embedding: np.ndarray, audio: np.ndarray,
             t_d: float, t_c: float, origin: str) -> None:
        """Add a new deferred segment to the buffer after eviction cleanup."""
        if not self.enabled:
            return

        # Eviction sweep
        self._evict_expired()
        self._evict_over_retried()

        # FIFO eviction if still full
        while len(self.segments) >= self.max_segments:
            evicted = self.segments.pop(0)
            logger.debug(
                f"[DeferredBuffer] FIFO evict — origin={evicted.origin}, "
                f"age={time.time() - evicted.created_at:.1f}s"
            )

        seg = DeferredSegment(
            embedding=embedding,
            audio=audio,
            t_d=t_d,
            t_c=t_c,
            origin=origin,
            created_at=time.time(),
        )
        self.segments.append(seg)
        logger.debug(
            f"[DeferredBuffer] Pushed segment — origin={origin}, "
            f"t_d={t_d:.3f}, t_c={t_c:.3f}, buffer_size={len(self.segments)}"
        )

    def get_valid_segments(self) -> list[DeferredSegment]:
        """Return segments that are still within TTL and retry limits."""
        now = time.time()
        return [
            s for s in self.segments
            if (now - s.created_at) <= self.max_age_seconds
            and s.retry_count < self.max_retries
        ]

    def remove(self, segment: DeferredSegment) -> None:
        """Remove a specific segment after successful reconciliation."""
        try:
            self.segments.remove(segment)
        except ValueError:
            pass  # Already removed or not found

    def reset(self) -> None:
        """Clear all deferred segments (called on new session)."""
        count = len(self.segments)
        self.segments.clear()
        if count > 0:
            logger.info(f"[DeferredBuffer] Reset — cleared {count} segments")

    def get_stats(self) -> dict:
        """Return debug statistics about the buffer state."""
        now = time.time()
        valid = self.get_valid_segments()
        origins = {}
        for s in self.segments:
            origins[s.origin] = origins.get(s.origin, 0) + 1

        return {
            "total_segments": len(self.segments),
            "valid_segments": len(valid),
            "by_origin": origins,
            "oldest_age_seconds": round(now - self.segments[0].created_at, 1) if self.segments else 0,
            "enabled": self.enabled,
        }

    # ------------------------------------------------------------------
    # Internal eviction helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        """Remove segments older than max_age_seconds."""
        now = time.time()
        before = len(self.segments)
        self.segments = [
            s for s in self.segments
            if (now - s.created_at) <= self.max_age_seconds
        ]
        evicted = before - len(self.segments)
        if evicted > 0:
            logger.debug(f"[DeferredBuffer] Evicted {evicted} expired segments")

    def _evict_over_retried(self) -> None:
        """Remove segments that exceeded max_retries."""
        before = len(self.segments)
        self.segments = [
            s for s in self.segments
            if s.retry_count < self.max_retries
        ]
        evicted = before - len(self.segments)
        if evicted > 0:
            logger.debug(f"[DeferredBuffer] Evicted {evicted} over-retried segments")
