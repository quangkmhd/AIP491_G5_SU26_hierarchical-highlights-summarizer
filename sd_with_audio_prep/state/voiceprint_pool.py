import os
import json
import numpy as np
from typing import Tuple
from config.paths import get_full_path

class VoiceprintPool:
    def __init__(self, config: dict = None):
        self.config = config or {}
        pool_cfg = self.config.get("module2_diarization", {}).get("voiceprint_pool", {})
        
        self.profiles = {} 
        self.next_id = 1
        
        # Storage directory on disk
        save_dir = pool_cfg.get("save_dir", "results/pool_state")
        self.save_dir = get_full_path(save_dir)
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)
            
        # Base EMA coefficient (base learning rate for profiles)
        # alpha = 0.1 means new data contributes max 10%, old data retains 90%
        self.base_alpha = pool_cfg.get("base_alpha", 0.1)
        
        # Auto-reload pool from disk if available (supports crash recovery)
        self.load_from_disk()
        
    def get_size(self) -> int:
        return len(self.profiles)
        
    def reset(self):
        """Reset the entire Pool for a new meeting."""
        self.profiles = {}
        self.next_id = 1
        # Delete old files
        if os.path.exists(self.save_dir):
            for f in os.listdir(self.save_dir):
                if f.endswith(".npy") or f.endswith(".json"):
                    os.remove(os.path.join(self.save_dir, f))
        
    def load_from_disk(self):
        """Restore Pool state from disk, including reference_audio"""
        meta_path = os.path.join(self.save_dir, "pool_metadata.json")
        if not os.path.exists(meta_path):
            return
            
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            for spk_id, meta in metadata.items():
                emb_path = os.path.join(self.save_dir, f"{spk_id}_emb.npy")
                audio_path = os.path.join(self.save_dir, f"{spk_id}_audio.npy")
                
                if os.path.exists(emb_path):
                    embedding = np.load(emb_path)
                    reference_audio = np.load(audio_path) if os.path.exists(audio_path) else None
                    
                    self.profiles[spk_id] = {
                        "embedding": embedding,
                        "confidence": meta.get("confidence", 1.0),
                        "last_active": meta.get("last_active", 0.0),
                        "reference_audio": reference_audio,
                        "update_count": meta.get("update_count", 0)
                    }
                    
                    # Update next_id to prevent duplicates
                    try:
                        num = int(spk_id.split("_")[1])
                        if num >= self.next_id:
                            self.next_id = num + 1
                    except Exception:
                        pass
        except Exception as e:
            print(f"[VoiceprintPool] Error loading state from disk: {e}")

    def _save_to_disk(self):
        """Overwrite the entire Pool state to disk for tracking"""
        metadata = {}
        for spk_id, data in self.profiles.items():
            metadata[spk_id] = {
                "confidence": data["confidence"],
                "last_active": data["last_active"],
                "update_count": data.get("update_count", 0)
            }
            # Save embedding as npy
            np.save(os.path.join(self.save_dir, f"{spk_id}_emb.npy"), data["embedding"])
            # Save reference_audio as well to recover for Branch B (TSE)
            if data.get("reference_audio") is not None:
                np.save(os.path.join(self.save_dir, f"{spk_id}_audio.npy"), data["reference_audio"])
        # Save meta information to JSON for human readability
        with open(os.path.join(self.save_dir, "pool_metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4)
        
    def update_profile(self, embedding: np.ndarray, last_active_time: float, speaker_id: str = None, confidence: float = 1.0, reference_audio: np.ndarray = None) -> str:
        """Add new or update a Speaker's profile using EMA"""
        if speaker_id is None or speaker_id not in self.profiles:
            speaker_id = f"SPK_{self.next_id:03d}"
            self.next_id += 1
            # Completely new addition
            self.profiles[speaker_id] = {
                "embedding": embedding,
                "confidence": confidence,
                "last_active": last_active_time,
                "reference_audio": reference_audio,
                "update_count": 1
            }
        else:
            # ID exists -> Update EMA (balance between old and new)
            old_emb = self.profiles[speaker_id]["embedding"]
            
            # Dynamic Alpha: The higher the confidence, the more it learns (max is base_alpha)
            dynamic_alpha = min(self.base_alpha, self.base_alpha * confidence)
            new_emb = dynamic_alpha * embedding + (1 - dynamic_alpha) * old_emb
            
            # Restore magnitude (L2 normalization) after interpolation
            norm = np.linalg.norm(new_emb)
            if norm > 0:
                new_emb = new_emb / norm
                
            self.profiles[speaker_id]["embedding"] = new_emb
            self.profiles[speaker_id]["confidence"] = confidence
            self.profiles[speaker_id]["last_active"] = last_active_time
            self.profiles[speaker_id]["update_count"] += 1
            
            if reference_audio is not None:
                self.profiles[speaker_id]["reference_audio"] = reference_audio

        # Synchronize save to disk
        self._save_to_disk()
        
        return speaker_id
        
    def find_best_match(self, embedding: np.ndarray) -> Tuple[str, float, str, float]:
        """
        Finds the top 2 closest matches in the Pool based on Cosine Similarity.
        Returns: (id_1, score_1, id_2, score_2)
        """
        if not self.profiles:
            return None, 0.0, None, 0.0
            
        scores = []
        for spk_id, prof_data in self.profiles.items():
            prof_emb = prof_data["embedding"]
            # Calculate Cosine Similarity
            dot = np.dot(embedding, prof_emb)
            norm_a = np.linalg.norm(embedding)
            norm_b = np.linalg.norm(prof_emb)
            sim = dot / (norm_a * norm_b)
            scores.append((spk_id, sim))
            
        # Sort descending by similarity score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        id_1, score_1 = scores[0]
        id_2, score_2 = scores[1] if len(scores) > 1 else (None, 0.0)
        
        return id_1, score_1, id_2, score_2

    def update_last_active(self, speaker_id: str, timestamp: float):
        """Updates the last active time without poisoning the embedding (Golden Rule)."""
        if speaker_id in self.profiles:
            self.profiles[speaker_id]["last_active"] = timestamp
            # Do not call _save_to_disk() here to avoid disk wear and I/O bottlenecks.
            # last_active state will be piggybacked during the next update_profile.
