"""
Module 2: Speaker Diarization Pipeline
Handles speaker identification, overlap detection, and routing using the Variable VAD Chunking architecture.
"""
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)


class SpeakerDiarization:
    def __init__(self, ovd, embedder, tse, bss, pool, config, vad=None):
        self.ovd = ovd
        self.embedder = embedder
        self.tse = tse
        self.bss = bss
        self.pool = pool
        self.config = config
        self.vad = vad

        config_module2 = self.config.get("module2_diarization", {})
        self.config_branch_a = config_module2.get("branch_a_single_speaker", {})
        self.config_branch_b = config_module2.get("branch_b_overlap_tse", {})
        self.config_post_vad = config_module2.get("post_vad", {})
        self.matching_threshold = self.config_branch_a.get("matching_threshold", 0.5)

    def reset_session(self):
        """
        Resets the state for a new session (e.g., a new meeting).
        Clears the OVD buffer to prevent overlap noise from previous sessions.
        """
        if hasattr(self.ovd, 'reset'):
            self.ovd.reset()
        logger.info("[Diarization] Session state reset successful (OVD buffer cleared).")

    def _apply_post_vad(self, stream: np.ndarray) -> tuple[np.ndarray, bool, float, float]:
        """Post-processing filter: Evaluates the quality of a separated stream."""
        if not self.vad:
            return stream, True, 2.5, 1.0
        
        t_d, t_c = self.vad.process(stream)
        
        # Calculate dynamic theta_dur based on the actual chunk length
        sr = self.config.get("audio", {}).get("sample_rate", 16000)
        chunk_length_s = len(stream) / sr
        
        # Get base_theta_dur from config, but if the chunk is very short, use a relative threshold (30%)
        # Example: 0.5s chunk -> 30% = 0.15s, but minimum min_dur should be 0.25s
        base_dur = self.config_post_vad.get("theta_dur", 0.8)
        dynamic_theta_dur = min(base_dur, max(0.25, 0.3 * chunk_length_s))
        
        theta_conf = self.config_post_vad.get("theta_conf", 0.75)
        
        is_valid = (t_d > dynamic_theta_dur) and (t_c > theta_conf)
        return stream, is_valid, t_d, t_c

    def _identify_only(self, stream: np.ndarray, current_time: float) -> str:
        """Identifies the speaker and ONLY updates last_active (Complies with Golden Rule)"""
        emb = self.embedder.extract(stream)
        id_1, score_1, _, _ = self.pool.find_best_match(emb)
        
        if id_1 and score_1 > self.matching_threshold:
            self.pool.update_last_active(id_1, current_time)
            return id_1
        return "UNKNOWN"

    def process(self, clean_audio: np.ndarray, t_d: float, t_c: float) -> dict:
        """
        Processes identification according to the Pipeline Architecture (New Design).
        Input is a cleaned, variable-length chunk (Variable Chunking).
        """
        current_time = time.time()
        
        # 1. Overlap detection
        has_overlap = self.ovd.detect_overlap(clean_audio)

        result = {
            "status": "SUCCESS",
            "has_overlap": has_overlap,
            "speakers": [],
            "speaker_details": [],
            "audio_streams": []
        }

        sr = self.config.get("audio", {}).get("sample_rate", 16000)

        # NO OVERLAP -> BRANCH A (Embed & Update Pool)
        if not has_overlap:
            result["branch"] = "BRANCH_A"
            emb = self.embedder.extract(clean_audio)
            id_1, score_1, _, _ = self.pool.find_best_match(emb)
            matched_id = id_1 if (id_1 and score_1 > self.matching_threshold) else None

            # Quality Gate for Pool update (Only Branch A is allowed to perform EMA updates)
            pool_cfg = self.config_branch_a.get("pool_update", {})
            if t_d > pool_cfg.get("theta_dur", 0.8) and t_c > pool_cfg.get("theta_conf", 0.75):
                matched_id = self.pool.update_profile(
                    emb, current_time, speaker_id=matched_id, confidence=t_c, reference_audio=clean_audio
                )
            
            spk_name = matched_id if matched_id else "UNKNOWN"
            dur_sec = float(len(clean_audio) / sr)
            result["speakers"].append(spk_name)
            result["speaker_details"].append({"speaker": spk_name, "speech_duration_sec": round(dur_sec, 3)})
            result["audio_streams"].append(clean_audio)
            return result

        # HAS OVERLAP -> Use Heuristic Routing
        theta_low = self.config_branch_b.get("theta_low", 0.45)
        theta_very_low = self.config_branch_b.get("theta_very_low", 0.35)

        # Extract Mix embedding purely for heuristic hint scores
        emb_mix = self.embedder.extract(clean_audio)
        id_1, s_top1, id_2, s_top2 = self.pool.find_best_match(emb_mix)

        # Decision Router (TSE or BSS)
        primary_branch = "BRANCH_B_TSE" if (s_top1 > theta_low and s_top2 > theta_very_low) else "BRANCH_C_BSS"
        branches_to_try = [primary_branch, "BRANCH_C_BSS" if primary_branch == "BRANCH_B_TSE" else "BRANCH_B_TSE"]

        for branch in branches_to_try:
            if branch == "BRANCH_B_TSE":
                prof1 = self.pool.profiles.get(id_1)
                prof2 = self.pool.profiles.get(id_2)
                # Retrieve raw audio from TSE
                raw_streams = [audio for audio, _ in self.tse.extract_targets(clean_audio, prof1, prof2)]
            else:
                raw_streams = self.bss.separate(clean_audio)

            # Post-VAD and Identification (Identify ONLY)
            valid_found = False
            temp_speakers = []
            temp_details = []
            temp_streams = []
            
            logger.debug(f"[Overlap] Testing branch {branch}. raw_streams count: {len(raw_streams)}")
            for idx, stream in enumerate(raw_streams):
                energy = np.sqrt(np.mean(stream**2)) if len(stream) > 0 else 0.0
                logger.debug(f"[Overlap] {branch} Stream {idx}: shape={stream.shape}, energy={energy:.6f}")
                clean_stream, is_valid, t_d, t_c = self._apply_post_vad(stream)
                logger.debug(f"[Overlap] {branch} Post-VAD Stream {idx}: is_valid={is_valid}, t_d={t_d:.3f}, t_c={t_c:.3f}")
                
                s_dur = float(len(clean_stream) / sr)
                if is_valid:
                    valid_found = True
                    spk_id = self._identify_only(clean_stream, current_time)
                else:
                    spk_id = "UNKNOWN"

                temp_speakers.append(spk_id)
                temp_details.append({"speaker": spk_id, "speech_duration_sec": round(s_dur, 3)})
                temp_streams.append(clean_stream)

            if valid_found:
                result["branch"] = branch
                result["speakers"].extend(temp_speakers)
                result["speaker_details"].extend(temp_details)
                result["audio_streams"].extend(temp_streams)
                return result

        # If all extracted streams (from both branches) are garbage -> Fallback returns the original Mix Audio
        logger.warning("[Overlap] Both BSS and TSE failed (generated garbage). Fallback activated.")
        return self._fallback(clean_audio)

    def _fallback(self, mix_audio: np.ndarray) -> dict:
        """FALLBACK_RAW: Keeps the mixture intact, assigns unresolved_overlap label."""
        sr = self.config.get("audio", {}).get("sample_rate", 16000)
        dur_sec = float(len(mix_audio) / sr)
        return {
            "status": "FALLBACK_RAW",
            "branch": "FALLBACK",
            "has_overlap": True,
            "speakers": ["unresolved_overlap"],
            "speaker_details": [{"speaker": "unresolved_overlap", "speech_duration_sec": round(dur_sec, 3)}],
            "audio_streams": [mix_audio]
        }
