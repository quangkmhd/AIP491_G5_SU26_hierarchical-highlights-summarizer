import numpy as np
from core.buffer import SmartAudioBuffer

class AudioPreprocessing:
    def __init__(self, denoiser, vad, config):
        self.denoiser = denoiser
        self.vad = vad
        self.config = config
        
        # Read threshold configs from settings.yaml
        qgate_cfg = self.config.get("module1_preprocessing", {}).get("quality_gate", {})
        self.theta_dur = qgate_cfg.get("theta_dur", 0.25)
        self.theta_conf = qgate_cfg.get("theta_conf", 0.5)
        
        # Initialize SmartAudioBuffer
        self.buffer = SmartAudioBuffer(config, vad_model=vad)

    def reset_session(self):
        self.buffer.reset()
        
    def process_chunk(self, frame: np.ndarray) -> dict:
        """
        Receives a small frame (e.g., 0.5s) and pushes it to the Buffer (VAD scans the raw frame).
        If the Buffer outputs a complete chunk, it goes through denoising and the Quality Gate.
        """
        # Step 1: Accumulate raw frame directly into Buffer
        full_chunk = self.buffer.process_stream_chunk(frame)
        
        if full_chunk is None:
            return {
                "status": "BUFFERING",
                "clean_audio": None,
                "t_d": 0.0,
                "t_c": 0.0
            }
            
        # Step 2: Denoise the ENTIRE chunk sequentially (Optimizes CPU & DFN Context)
        clean_chunk = self.denoiser.process(full_chunk)
            
        # Step 3: Pass through the Decision Gate (Quality Gate) on the clean chunk
        t_d, t_c = self.vad.process(clean_chunk)
        
        if t_d > self.theta_dur and t_c > self.theta_conf:
            return {
                "status": "PASS",
                "clean_audio": clean_chunk,
                "t_d": t_d,
                "t_c": t_c
            }
        else:
            return {
                "status": "DROP",
                "clean_audio": clean_chunk,
                "t_d": t_d,
                "t_c": t_c
            }
            
    def flush(self) -> dict:
        """Forcibly flushes the remaining chunk out of the buffer."""
        full_chunk = self.buffer.flush()
        if full_chunk is None:
            return None
            
        # Centralized denoising
        clean_chunk = self.denoiser.process(full_chunk)
            
        t_d, t_c = self.vad.process(clean_chunk)
        if t_d > self.theta_dur and t_c > self.theta_conf:
            return {
                "status": "PASS",
                "clean_audio": clean_chunk,
                "t_d": t_d,
                "t_c": t_c
            }
        else:
            return {
                "status": "DROP",
                "clean_audio": clean_chunk,
                "t_d": t_d,
                "t_c": t_c
            }
