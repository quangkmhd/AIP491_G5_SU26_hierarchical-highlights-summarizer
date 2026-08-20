import numpy as np
import logging
import time

logger = logging.getLogger(__name__)

class SmartAudioBuffer:
    """Smart Audio Buffer to cut chunks dynamically based on VAD.
    Accumulates small audio streams, checks for silence, and cuts complete chunks.
    """
    def __init__(self, config: dict, vad_model):
        self.config = config
        self.vad_model = vad_model
        self.sr = config.get("audio", {}).get("sample_rate", 16000)
        
        cfg = config.get("module2_diarization", {}).get("smart_buffer", {})
        self.chunk_size_ms = cfg.get("chunk_size_ms", 500)
        self.min_speech_ms = cfg.get("min_speech_duration_ms", 250)
        self.min_silence_ms = cfg.get("min_silence_duration_ms", 500)
        self.max_speech_s = cfg.get("max_speech_duration_s", 10.0)
        self.vad_threshold = cfg.get("vad_threshold", 0.5)
        
        self.min_silence_samples = int(self.sr * self.min_silence_ms / 1000)
        self.min_speech_samples = int(self.sr * self.min_speech_ms / 1000)
        self.max_speech_samples = int(self.sr * self.max_speech_s)
        
        self.reset()
        
    def reset(self):
        self.buffer = np.array([], dtype=np.float32)
        self.is_speaking = False
        self.silence_samples_count = 0
        
    def process_stream_chunk(self, chunk: np.ndarray):
        """
        Receive a small chunk (e.g., 500ms) and return a complete Chunk if break conditions are met.
        If conditions are not met, return None.
        """
        # Analyze VAD on small chunk
        t_d, t_c = self.vad_model.process(chunk)
        has_speech = t_c > self.vad_threshold
        
        # If not speaking and speech detected -> Start recording
        if not self.is_speaking and has_speech:
            self.is_speaking = True
            self.silence_samples_count = 0
            
        if self.is_speaking:
            self.buffer = np.concatenate((self.buffer, chunk))
            
            if not has_speech:
                self.silence_samples_count += len(chunk)
            else:
                self.silence_samples_count = 0
                
            # Check break conditions:
            # 1. Minimum silence reached
            # 2. Maximum duration exceeded
            if self.silence_samples_count >= self.min_silence_samples or len(self.buffer) >= self.max_speech_samples:
                output_chunk = self.buffer.copy()
                self.reset()
                
                # Discard if actual speech duration is too short
                if len(output_chunk) < self.min_speech_samples:
                    return None
                    
                return output_chunk
                
        return None
        
    def flush(self):
        """Force return current chunk in buffer (for end of stream or testing)"""
        if self.is_speaking and len(self.buffer) > 0:
            output_chunk = self.buffer.copy()
            self.reset()
            if len(output_chunk) < self.min_speech_samples:
                return None
            return output_chunk
        return None
