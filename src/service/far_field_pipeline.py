from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Protocol

import numpy as np

from src.types.audio import AudioQualityMetrics, FinalUtteranceEvent
from src.types.audio import AudioSessionStart

from .audio_capture import StreamingAudioSession, cleanup_expired_recordings
from .audio_preprocessor import AudioPreprocessor, Enhancer, ProcessedAudioChunk
from .diarization_engine import (
    DiarizationEngine,
    DiarizationResult,
    SherpaSpeakerEmbedder,
)


class AudioSession(Protocol):
    source_rate: int

    def push(self, samples: np.ndarray) -> np.ndarray: ...
    def flush(self) -> np.ndarray: ...
    def close(self, *, retain: bool = True) -> Path: ...


class Preprocessor(Protocol):
    def process(self, samples: np.ndarray) -> list[ProcessedAudioChunk]: ...
    def flush(self) -> list[ProcessedAudioChunk]: ...


class VadSpeechSegment:
    def __init__(
        self,
        samples: np.ndarray,
        start_sample: int,
        end_sample: int,
        confidence: float,
    ) -> None:
        self.samples = samples
        self.start_sample = start_sample
        self.end_sample = end_sample
        self.confidence = confidence


class VadProcessor(Protocol):
    def accept(self, chunk: ProcessedAudioChunk) -> list[VadSpeechSegment]: ...
    def flush(self) -> list[VadSpeechSegment]: ...


class Diarizer(Protocol):
    def process(
        self,
        enhanced_audio: np.ndarray,
        speaker_audio: np.ndarray,
        *,
        speech_duration: float,
        vad_confidence: float,
    ) -> DiarizationResult: ...


class SegmentRecognizer(Protocol):
    def decode_segment(self, samples: np.ndarray, sample_rate: int = 16000) -> str: ...


class FarFieldSession:
    """Own every stateful audio component for one WebSocket connection."""

    sample_rate = 16000

    def __init__(
        self,
        *,
        session_id: str,
        audio: AudioSession,
        preprocessor: Preprocessor,
        vad: VadProcessor,
        diarizer: Diarizer,
        asr: SegmentRecognizer,
    ) -> None:
        self.session_id = session_id
        self.audio = audio
        self.preprocessor = preprocessor
        self.vad = vad
        self.diarizer = diarizer
        self.asr = asr
        self._utterance_id = 0
        self._speaker_timeline = np.empty(0, dtype=np.float32)
        self._chunk_metrics: list[ProcessedAudioChunk] = []
        self._flushed = False
        self._empty_decodes = 0

    def push(self, samples: np.ndarray) -> tuple[FinalUtteranceEvent, ...]:
        if self._flushed:
            raise RuntimeError("far-field session was already flushed")
        resampled = self.audio.push(samples)
        return self._consume_resampled(resampled)

    def flush(self) -> tuple[FinalUtteranceEvent, ...]:
        if self._flushed:
            return ()
        self._flushed = True
        events: list[FinalUtteranceEvent] = []
        resampler_tail = self.audio.flush()
        if len(resampler_tail):
            events.extend(self._consume_resampled(resampler_tail))
        chunks = self.preprocessor.flush()
        events.extend(self._consume_chunks(chunks))
        events.extend(self._consume_speech(self.vad.flush()))
        return tuple(events)

    def close(self, *, retain: bool = True) -> Path:
        return self.audio.close(retain=retain)

    def _consume_resampled(self, samples: np.ndarray) -> tuple[FinalUtteranceEvent, ...]:
        if len(samples):
            self._speaker_timeline = np.concatenate((self._speaker_timeline, samples))
        return tuple(self._consume_chunks(self.preprocessor.process(samples)))

    def _consume_chunks(self, chunks: list[ProcessedAudioChunk]) -> list[FinalUtteranceEvent]:
        events: list[FinalUtteranceEvent] = []
        for chunk in chunks:
            self._chunk_metrics.append(chunk)
            events.extend(self._consume_speech(self.vad.accept(chunk)))
        return events

    def _consume_speech(self, segments: list[VadSpeechSegment]) -> list[FinalUtteranceEvent]:
        events: list[FinalUtteranceEvent] = []
        for speech in segments:
            speaker_audio = self._speaker_slice(speech)
            diarized = self.diarizer.process(
                speech.samples,
                speaker_audio,
                speech_duration=len(speech.samples) / self.sample_rate,
                vad_confidence=speech.confidence,
            )
            metric = self._metric_for(speech)
            for stream in diarized.streams:
                started = time.perf_counter()
                text = self.asr.decode_segment(stream.samples, self.sample_rate).strip()
                asr_ms = (time.perf_counter() - started) * 1000
                if not text:
                    self._empty_decodes += 1
                    continue
                self._utterance_id += 1
                preprocessing_ms = metric.preprocessing_ms if metric else 0.0
                rms, peak, clipped = self._signal_metrics(speech.samples, metric)
                total_ms = preprocessing_ms + diarized.latency_ms + asr_ms
                events.append(
                    FinalUtteranceEvent(
                        id=self._utterance_id,
                        session_id=self.session_id,
                        speaker=stream.speaker,
                        text=text,
                        start_sec=speech.start_sample / self.sample_rate,
                        end_sec=speech.end_sample / self.sample_rate,
                        source_sample_rate=self.audio.source_rate,
                        quality=AudioQualityMetrics(
                            rms=rms,
                            peak=peak,
                            clipped=clipped,
                            vad_confidence=speech.confidence,
                            speech_duration=len(speech.samples) / self.sample_rate,
                        ),
                        preprocessing_ms=preprocessing_ms,
                        diarization_ms=diarized.latency_ms,
                        asr_ms=asr_ms,
                        total_ms=total_ms,
                        fallback=stream.fallback,
                    )
                )
        return events

    def _speaker_slice(self, speech: VadSpeechSegment) -> np.ndarray:
        start = max(0, speech.start_sample)
        end = min(len(self._speaker_timeline), speech.end_sample)
        if end <= start:
            return speech.samples.copy()
        return self._speaker_timeline[start:end].copy()

    def _metric_for(self, speech: VadSpeechSegment) -> ProcessedAudioChunk | None:
        for chunk in reversed(self._chunk_metrics):
            if chunk.start_sample < speech.end_sample and chunk.end_sample > speech.start_sample:
                return chunk
        return None

    def _signal_metrics(
        self,
        samples: np.ndarray,
        metric: ProcessedAudioChunk | None,
    ) -> tuple[float, float, bool]:
        if metric is not None:
            return metric.rms, metric.peak, metric.clipped
        magnitude = np.abs(samples)
        rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))) if len(samples) else 0.0
        peak = float(np.max(magnitude)) if len(samples) else 0.0
        return rms, peak, bool(np.any(magnitude >= 0.999))


class SherpaVadProcessor:
    """Feed fixed windows to a per-session sherpa-onnx VAD and expose its timeline."""

    def __init__(self, vad: object, window_size: int, sample_rate: int = 16000) -> None:
        self.vad = vad
        self.window_size = window_size
        self.sample_rate = sample_rate
        self._tail = np.empty(0, dtype=np.float32)
        self._accepted_samples = 0

    def accept(self, chunk: ProcessedAudioChunk) -> list[VadSpeechSegment]:
        self._tail = np.concatenate((self._tail, chunk.samples))
        while len(self._tail) >= self.window_size:
            window = self._tail[: self.window_size]
            self.vad.accept_waveform(window)
            self._tail = self._tail[self.window_size :]
            self._accepted_samples += self.window_size
        return self._drain()

    def flush(self) -> list[VadSpeechSegment]:
        if len(self._tail):
            original_length = len(self._tail)
            padded = np.pad(self._tail, (0, self.window_size - original_length))
            self.vad.accept_waveform(padded.astype(np.float32, copy=False))
            self._accepted_samples += original_length
            self._tail = np.empty(0, dtype=np.float32)
        self.vad.flush()
        return self._drain()

    def _drain(self) -> list[VadSpeechSegment]:
        output: list[VadSpeechSegment] = []
        while not self.vad.empty():
            segment = self.vad.front
            samples = np.asarray(segment.samples, dtype=np.float32)
            start = int(getattr(segment, "start", self._accepted_samples - len(samples)))
            self.vad.pop()
            output.append(
                VadSpeechSegment(
                    samples=samples,
                    start_sample=max(0, start),
                    end_sample=max(0, start) + len(samples),
                    confidence=1.0,
                )
            )
        return output


class DefaultFarFieldSessionFactory:
    """Create isolated session state around shared inference models."""

    def __init__(
        self,
        *,
        config: object,
        asr: object,
        enhancer: Enhancer,
        recordings_root: Path,
    ) -> None:
        if getattr(asr, "embedding_extractor", None) is None:
            raise RuntimeError("speaker embedding model is required for accuracy mode")
        self.config = config
        self.asr = asr
        self.enhancer = enhancer
        self.recordings_root = recordings_root
        cleanup_expired_recordings(
            recordings_root,
            int(getattr(config, "audio_retention_hours")),
        )

    def create(self, start: AudioSessionStart) -> FarFieldSession:
        session_id = uuid.uuid4().hex
        audio = StreamingAudioSession(
            session_id,
            start.sample_rate,
            self.recordings_root,
        )
        preprocessor = AudioPreprocessor(
            self.enhancer,
            sample_rate=16000,
            chunk_seconds=float(getattr(self.config, "preprocessing_chunk_seconds")),
            overlap_seconds=float(getattr(self.config, "preprocessing_overlap_seconds")),
        )
        vad = SherpaVadProcessor(
            getattr(self.asr, "create_vad")(),
            int(getattr(self.asr, "vad_window_size")),
        )
        diarizer = DiarizationEngine(
            embedder=SherpaSpeakerEmbedder(getattr(self.asr, "embedding_extractor")),
            matching_threshold=float(getattr(self.config, "speaker_similarity_threshold")),
        )
        return FarFieldSession(
            session_id=session_id,
            audio=audio,
            preprocessor=preprocessor,
            vad=vad,
            diarizer=diarizer,
            asr=self.asr,
        )


__all__ = [
    "DefaultFarFieldSessionFactory",
    "FarFieldSession",
    "SherpaVadProcessor",
    "VadSpeechSegment",
]
