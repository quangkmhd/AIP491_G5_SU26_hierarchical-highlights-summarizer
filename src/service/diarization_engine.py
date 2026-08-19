from __future__ import annotations

import time
from typing import Any

import numpy as np


class DiarizedStream:
    def __init__(self, speaker: str, samples: np.ndarray) -> None:
        self.speaker = speaker
        self.samples = samples
        self.fallback = False


class DiarizationResult:
    def __init__(self, speaker: str, samples: np.ndarray, latency_ms: float) -> None:
        self.streams = (DiarizedStream(speaker, samples),)
        self.has_overlap = False
        self.latency_ms = latency_ms


class DiarizationEngine:
    """Identify sequential speakers for meeting audio."""

    def __init__(
        self,
        embedder: Any,
        *,
        matching_threshold: float = 0.65,
        profile_min_duration: float = 1.5,
        profile_min_confidence: float = 0.9,
    ) -> None:
        self.embedder = embedder
        self.matching_threshold = matching_threshold
        self.profile_min_duration = profile_min_duration
        self.profile_min_confidence = profile_min_confidence
        self.profiles: list[dict[str, Any]] = []

    def profile_count(self) -> int:
        return len(self.profiles)

    def extract_embedding(self, samples: np.ndarray) -> np.ndarray:
        stream = self.embedder.create_stream()
        stream.accept_waveform(16000, samples)
        stream.input_finished()
        return np.asarray(self.embedder.compute(stream), dtype=np.float32).reshape(-1)

    def process(
        self,
        enhanced_audio: np.ndarray,
        speaker_audio: np.ndarray,
        *,
        speech_duration: float,
        vad_confidence: float,
    ) -> DiarizationResult:
        started = time.perf_counter()
        speaker = self._identify(speaker_audio, speech_duration, vad_confidence)
        latency_ms = (time.perf_counter() - started) * 1000
        return DiarizationResult(speaker, enhanced_audio.copy(), latency_ms)

    def _identify(self, audio: np.ndarray, duration: float, confidence: float) -> str:
        if self.embedder is None:
            return "Speaker 01"
        emb = self.extract_embedding(audio)
        norm = float(np.linalg.norm(emb))
        if norm <= 1e-6 or not np.isfinite(emb).all():
            return "Unknown Speaker"
        emb = (emb / norm).astype(np.float32)

        best_score, best_prof = -1.0, None
        for prof in self.profiles:
            score = float(np.dot(emb, prof["centroid"]))
            if score > best_score:
                best_score, best_prof = score, prof

        good_ref = duration >= self.profile_min_duration and confidence >= self.profile_min_confidence

        if best_prof and best_score >= self.matching_threshold:
            if good_ref:
                w = min(best_prof["obs"], 9)
                merged = (best_prof["centroid"] * w + emb) / (w + 1)
                m_norm = float(np.linalg.norm(merged))
                if m_norm > 1e-6:
                    best_prof["centroid"] = (merged / m_norm).astype(np.float32)
                best_prof["obs"] += 1
            return str(best_prof["speaker"])

        if good_ref:
            spk_name = f"Speaker {len(self.profiles) + 1:02d}"
            self.profiles.append({"speaker": spk_name, "centroid": emb, "obs": 1})
            return spk_name

        return "Unknown Speaker"

