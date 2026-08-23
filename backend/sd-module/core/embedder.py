"""Core Embedder — CAM++ Speaker Voiceprint Extraction Adapter."""

import logging
import os
import numpy as np
from config.paths import get_full_path, to_relative_path

logger = logging.getLogger(__name__)


class CAMPlusPlusEmbedder:
    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)

        local_path = config.get("model_paths", {}).get("cam_plus_plus")
        if local_path:
            local_path = get_full_path(local_path)

        if local_path and os.path.isdir(local_path):
            try:
                import contextlib
                import modelscope.utils.logger as ms_log
                ms_logger = ms_log.get_logger()
                ms_logger.setLevel(logging.ERROR)
                ms_logger.handlers.clear()

                from modelscope.pipelines import pipeline as ms_pipeline
                from modelscope.utils.constant import Tasks
                rel_path = to_relative_path(local_path)
                logger.info(f"[Embedder] Loading CAM++ model from local directory: '{rel_path}'...")
                
                with open(os.devnull, "w") as null_file:
                    with contextlib.redirect_stdout(null_file), contextlib.redirect_stderr(null_file):
                        self.pipeline = ms_pipeline(
                            task=Tasks.speaker_verification,
                            model=local_path
                        )
                self.use_raw_onnx = False
                logger.info("[Embedder] CAM++ Voiceprint Embedder loaded successfully (512-dim embedding).")
            except Exception as e:
                raise RuntimeError(f"[Embedder] Cannot load CAM++ from local folder '{local_path}': {e}")
        else:
            try:
                from modelscope.pipelines import pipeline as ms_pipeline
                from modelscope.utils.constant import Tasks
                logger.info("[Embedder] Loading CAM++ model from ModelScope online repository...")
                self.pipeline = ms_pipeline(
                    task=Tasks.speaker_verification,
                    model="iic/speech_campplus_sv_zh-cn_16k-common"
                )
                logger.info("[Embedder] CAM++ Voiceprint Embedder loaded successfully.")
            except Exception as e:
                raise RuntimeError(f"[Embedder] Cannot load CAM++ from ModelScope repository: {e}")

    def extract(self, audio_chunk: np.ndarray) -> np.ndarray:
        """Extract a 512-dimensional speaker voiceprint embedding vector."""
        if self.pipeline is None:
            raise RuntimeError("[Embedder] CAM++ Pipeline has not been initialized!")

        try:
            try:
                result = self.pipeline([audio_chunk], output_emb=True)
            except Exception:
                result = self.pipeline(audio_chunk)

            if isinstance(result, list) and len(result) > 0:
                result = result[0]

            if isinstance(result, dict) and "embs" in result:
                emb = result["embs"]
            elif isinstance(result, dict) and "embedding" in result:
                emb = result["embedding"]
            else:
                emb = result

            if isinstance(emb, list):
                emb = np.array(emb, dtype=np.float32)

            if hasattr(emb, "detach"):
                emb = emb.detach().cpu().numpy()

            emb = np.squeeze(emb).astype(np.float32)

            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm

            return emb
        except Exception as e:
            logger.error(f"[Embedder] Voiceprint extraction failed: {e}")
            return np.zeros(512, dtype=np.float32)