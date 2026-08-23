import numpy as np
import logging
import os
import onnxruntime as ort
from config.paths import get_full_path

logger = logging.getLogger(__name__)


class CAMPlusPlusEmbedder:
    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("audio", {}).get("sample_rate", 16000)

        local_path = config.get("model_paths", {}).get("cam_plus_plus")
        
        # Resolve relative path
        if local_path:
            local_path = get_full_path(local_path)

        if local_path and os.path.isdir(local_path):
            # Mode 1: ModelScope from local folder (NO INTERNET REQUIRED, keeps preprocessing pipeline intact)
            try:
                from modelscope.pipelines import pipeline as ms_pipeline
                from modelscope.utils.constant import Tasks
                logger.info(f"[Embedder] Loading CAM++ from local directory via ModelScope: {local_path}")
                self.pipeline = ms_pipeline(
                    task=Tasks.speaker_verification,
                    model=local_path
                )
                self.use_raw_onnx = False
                logger.info("[Embedder] CAM++ successfully loaded from local folder.")
            except Exception as e:
                raise RuntimeError(f"[Embedder] Critical Error: Cannot load CAM++ from local folder: {e}")
        else:
            # Mode 2: ModelScope from Internet (default if no local_path)
            try:
                from modelscope.pipelines import pipeline as ms_pipeline
                from modelscope.utils.constant import Tasks
                logger.info("[Embedder] Loading CAM++ from ModelScope internet...")
                self.pipeline = ms_pipeline(
                    task=Tasks.speaker_verification,
                    model='iic/speech_campplus_sv_zh-cn_16k-common'
                )
                logger.info("[Embedder] CAM++ load successful.")
            except Exception as e:
                raise RuntimeError(f"[Embedder] Critical Error: Cannot load CAM++ from internet: {e}")

    def extract(self, audio_chunk: np.ndarray) -> np.ndarray:
        if self.pipeline is None:
            raise RuntimeError("[Embedder] Pipeline has not been initialized!")
            
        try:
            # Try list format (newer ModelScope versions)
            try:
                result = self.pipeline([audio_chunk], output_emb=True)
            except Exception:
                # Fallback to single array (older ModelScope versions)
                result = self.pipeline(audio_chunk)

            if isinstance(result, dict) and 'embs' in result:
                emb = np.array(result['embs'], dtype=np.float32)
            elif isinstance(result, dict) and 'spk_embedding' in result:
                emb = np.array(result['spk_embedding'], dtype=np.float32)
            elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and 'embs' in result[0]:
                emb = np.array(result[0]['embs'], dtype=np.float32)
            elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and 'spk_embedding' in result[0]:
                emb = np.array(result[0]['spk_embedding'], dtype=np.float32)
            elif isinstance(result, np.ndarray):
                emb = result.astype(np.float32)
            else:
                raise ValueError(f"[Embedder] Unknown output format: {type(result)}")
                
            emb = emb.flatten()
            return self._l2_normalize(emb)
        except Exception as e:
            logger.error(f"[Embedder] Embedding extraction error: {e}")
            raise e

    @staticmethod
    def _l2_normalize(embedding: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding