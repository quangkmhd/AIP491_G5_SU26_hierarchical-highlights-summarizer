"""
Module 2: Speaker Diarization Pipeline
Handles speaker identification, overlap detection, and routing using the Variable VAD Chunking architecture.
"""
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)


class SpeakerDiarization:
    def __init__(self, ovd, embedder, tse, bss, pool, config, vad=None, deferred_buffer=None):
        self.ovd = ovd
        self.embedder = embedder
        self.tse = tse
        self.bss = bss
        self.pool = pool
        self.config = config
        self.vad = vad
        self.deferred_buffer = deferred_buffer

        config_module2 = self.config.get("module2_diarization", {})
        self.config_branch_a = config_module2.get("branch_a_single_speaker", {})
        self.config_branch_b = config_module2.get("branch_b_overlap_tse", {})
        self.config_post_vad = config_module2.get("post_vad", {})
        self.matching_threshold = self.config_branch_a.get("matching_threshold", 0.5)

        # Reconcile config (DSR)
        cfg_reconcile = config_module2.get("deferred_buffer", {}).get("reconcile_gate", {})
        self.reconcile_alpha_factor = cfg_reconcile.get("alpha_factor", 0.5)

    def reset_session(self):
        """
        Resets the state for a new session (e.g., a new meeting).
        Clears the OVD buffer to prevent overlap noise from previous sessions.
        """
        if hasattr(self.ovd, 'reset'):
            self.ovd.reset()
        if self.deferred_buffer:
            self.deferred_buffer.reset()
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

    def _try_reconcile(self):
        """Scan DeferredBuffer and re-match against the latest pool state (DSR)."""
        if not self.deferred_buffer:
            return

        segments = self.deferred_buffer.get_valid_segments()
        if not segments:
            return

        reconciled = 0
        current_time = time.time()

        for seg in segments:
            seg.retry_count += 1
            id_1, score_1, _, _ = self.pool.find_best_match(seg.embedding)

            if not id_1 or score_1 <= self.matching_threshold:
                continue  # Still no match — keep in buffer

            if seg.origin == "BRANCH_A":
                # Matched → update profile with REDUCED alpha
                cfg = self.config.get("module2_diarization", {}).get("deferred_buffer", {})
                gate = cfg.get("reconcile_gate", {})
                r_theta_dur = gate.get("theta_dur", 0.6)
                r_theta_conf = gate.get("theta_conf", 0.65)

                if seg.t_d > r_theta_dur and seg.t_c > r_theta_conf:
                    self.pool.update_profile(
                        seg.embedding, current_time,
                        speaker_id=id_1,
                        confidence=seg.t_c,
                        reference_audio=seg.audio,
                        alpha_factor=self.reconcile_alpha_factor,
                    )
                    self.deferred_buffer.remove(seg)
                    reconciled += 1
                # If reconcile gate fails → keep in buffer for next attempt

            elif seg.origin == "OVERLAP_STREAM":
                # Overlap stream → only update last_active, NO EMA update
                self.pool.update_last_active(id_1, current_time)
                self.deferred_buffer.remove(seg)
                reconciled += 1

        if reconciled > 0:
            logger.info(f"[DSR] Reconciled {reconciled}/{len(segments)} deferred segments")

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
            quality_gate_passed = (
                t_d > pool_cfg.get("theta_dur", 0.8)
                and t_c > pool_cfg.get("theta_conf", 0.75)
            )

            if quality_gate_passed:
                matched_id = self.pool.update_profile(
                    emb, current_time, speaker_id=matched_id, confidence=t_c, reference_audio=clean_audio
                )
                # Trigger reconcile after successful pool update
                if self.deferred_buffer:
                    self._try_reconcile()
            else:
                # Quality Gate FAIL → cache segment for later reconciliation
                if self.deferred_buffer:
                    self.deferred_buffer.push(emb, clean_audio, t_d, t_c, "BRANCH_A")

            spk_name = matched_id if matched_id else "UNKNOWN"

            # Cache UNKNOWN due to no match (only if Quality Gate passed — gate-fail is handled above)
            if spk_name == "UNKNOWN" and quality_gate_passed and self.deferred_buffer:
                self.deferred_buffer.push(emb, clean_audio, t_d, t_c, "BRANCH_A")

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
