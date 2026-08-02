"""Implementation and Evaluation of Option B: True Incremental Streaming TextTiling Segmenter.

Implements stateful INITIALIZE / UPDATE / FLUSH streaming semantics with:
1. Stateful utterance buffer & window tracking.
2. Immutable boundary emission (once committed, boundaries cannot be revoked).
3. Commit zone lookahead (L = 20 utterances).
4. Short meeting & tail flush handling.
"""

from __future__ import annotations

import os
import sys
import time
import math
import numpy as np
import segeval
from sklearn.metrics import f1_score

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data import Corpus, EvalLoader
from src.config.sliding_text_tiling import SlidingTextTilingConfig
from src.service.sliding_text_tiling import (
    bow, cosine, similarity_scores, multiscale_depth, merge_small_segments, DEFAULT_RADII
)

class StreamingTextTilingSegmenter:
    """True incremental streaming TextTiling segmenter (Option B).
    
    Maintains internal state across UPDATE calls and commits immutable boundaries
    once they pass out of the lookahead horizon (Commit Zone).
    """

    def __init__(
        self,
        config: SlidingTextTilingConfig | None = None,
        stopwords: set[str] | None = None,
        lookahead: int = 20,
    ) -> None:
        self.config = config or SlidingTextTilingConfig()
        self.stopwords = stopwords or set()
        self.lookahead = lookahead
        self.reset()

    def reset(self) -> None:
        """INITIALIZE() - Reset all state for a new streaming session."""
        self.buffer: list[str] = []
        self.next_window_start: int = 0
        self.committed_boundaries: list[int] = []
        self.boundary_depths: dict[int, float] = {}
        self.pending_candidates: dict[int, float] = {}  # global_gap -> depth
        self.last_committed_index: int = -1

    def update(self, utterance: str) -> list[tuple[int, float]]:
        """UPDATE(u_t) - Ingest one utterance and return newly committed boundaries.
        
        Returns a list of newly committed boundary tuples: (global_boundary_index, depth_score).
        """
        self.buffer.append(utterance)
        n = len(self.buffer)
        W = self.config.window_size
        S = self.config.stride
        
        newly_committed: list[tuple[int, float]] = []

        # Check if we have enough utterances to evaluate a new window
        while n - self.next_window_start >= W:
            start = self.next_window_start
            win_utts = self.buffer[start : start + W]
            
            # Local window evaluation
            sim = similarity_scores(win_utts, block_size=self.config.block_size, stopwords=self.stopwords)
            if len(sim) >= 2:
                depth = multiscale_depth(
                    sim,
                    radii=self.config.radii,
                    agg=self.config.agg,
                    normalize_mode=self.config.normalize,
                )
                threshold = float(depth.mean() + self.config.alpha * depth.std())
                
                # Identify candidates in this window
                for j in range(len(depth)):
                    g = start + j
                    if g <= self.last_committed_index:
                        continue  # Already committed past this point
                    if depth[j] > threshold:
                        self.pending_candidates[g] = float(depth[j])

            # Commit Horizon: gaps at or before start + W - self.lookahead
            commit_cutoff = start + W - self.lookahead
            
            # Candidates eligible for commit
            eligible = sorted([g for g in self.pending_candidates if g <= commit_cutoff])
            
            if eligible:
                # Apply local greedy merging on eligible uncommitted candidates
                min_seg = max(2, int(W * self.config.min_segment_ratio))
                b_list = list(eligible)
                d_map = {g: self.pending_candidates[g] for g in b_list}
                
                # Include last committed boundary as left anchor if available
                left_anchor = self.last_committed_index
                
                # Merge small segments among eligible candidates
                merged = merge_small_segments(b_list, d_map, min_seg)
                
                for g in merged:
                    if g > self.last_committed_index:
                        depth_val = d_map[g]
                        self.committed_boundaries.append(g)
                        self.boundary_depths[g] = depth_val
                        self.last_committed_index = g
                        newly_committed.append((g, depth_val))
                        # Remove from pending
                        if g in self.pending_candidates:
                            del self.pending_candidates[g]
                            
                # Clean up any pending candidates <= commit_cutoff that were dropped during merging
                to_remove = [g for g in self.pending_candidates if g <= commit_cutoff]
                for g in to_remove:
                    del self.pending_candidates[g]

            self.next_window_start += S

        return newly_committed

    def flush(self) -> list[tuple[int, float]]:
        """FLUSH() - End of stream: evaluate tail buffer and force-close.
        
        Returns all remaining committed boundary tuples including the final force-close boundary.
        """
        n = len(self.buffer)
        newly_committed: list[tuple[int, float]] = []
        if n == 0:
            return []

        W = self.config.window_size

        if n <= W:
            # Short meeting (< W utterances): single batch pass over buffer
            sim = similarity_scores(self.buffer, block_size=self.config.block_size, stopwords=self.stopwords)
            if len(sim) >= 2:
                depth = multiscale_depth(
                    sim,
                    radii=self.config.radii,
                    agg=self.config.agg,
                    normalize_mode=self.config.normalize,
                )
                threshold = float(depth.mean() + self.config.alpha * depth.std())
                for j in range(len(depth)):
                    if depth[j] > threshold:
                        self.pending_candidates[j] = float(depth[j])
        else:
            # Pin final window to tail: n - W .. n
            start = n - W
            win_utts = self.buffer[start:n]
            sim = similarity_scores(win_utts, block_size=self.config.block_size, stopwords=self.stopwords)
            if len(sim) >= 2:
                depth = multiscale_depth(
                    sim,
                    radii=self.config.radii,
                    agg=self.config.agg,
                    normalize_mode=self.config.normalize,
                )
                threshold = float(depth.mean() + self.config.alpha * depth.std())
                for j in range(len(depth)):
                    g = start + j
                    if g > self.last_committed_index and depth[j] > threshold:
                        self.pending_candidates[g] = float(depth[j])

        # Final merging on all remaining uncommitted pending candidates
        uncommitted = sorted([g for g in self.pending_candidates if g > self.last_committed_index])
        if uncommitted:
            min_seg = max(2, int(min(n, W) * self.config.min_segment_ratio))
            d_map = {g: self.pending_candidates[g] for g in uncommitted}
            merged = merge_small_segments(uncommitted, d_map, min_seg)
            for g in merged:
                if g > self.last_committed_index:
                    depth_val = d_map[g]
                    self.committed_boundaries.append(g)
                    self.boundary_depths[g] = depth_val
                    self.last_committed_index = g
                    newly_committed.append((g, depth_val))

        # Force close at n - 1 if not already committed
        tail_index = n - 1
        if not self.committed_boundaries or self.committed_boundaries[-1] != tail_index:
            self.committed_boundaries.append(tail_index)
            self.boundary_depths[tail_index] = 0.0
            newly_committed.append((tail_index, 0.0))

        return newly_committed


def boundaries_to_binary(boundary_indices, total_entries):
    binary_list = [0] * total_entries
    for index in boundary_indices:
        if 0 <= index < total_entries:
            binary_list[index] = 1
    binary_list[-1] = 1
    return binary_list


def segments_to_binary(segment_sizes):
    total_length = sum(segment_sizes)
    binary_list = [0] * total_length
    end_indices = [sum(segment_sizes[:i+1]) for i in range(len(segment_sizes))]
    for index in end_indices[:-1]:
        binary_list[index - 1] = 1
    binary_list[-1] = 1
    return binary_list


def run_evaluation():
    import stopwordsiso
    stopwords = stopwordsiso.stopwords(["vi"])
    
    data_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eval_vi")
    loader = EvalLoader(data_root)

    config = SlidingTextTilingConfig(
        block_size=2,
        radii=[3, 5, 10, 15, 20],
        alpha=1.2,
        agg="mean",
        normalize="zscore",
        min_segment_ratio=0.20
    )

    print("=" * 80)
    print("EVALUATION: OPTION B (TRUE STREAMING) VS OPTION A (WINDOWED BATCH)")
    print("=" * 80)

    for corpus in Corpus:
        result = loader.load(corpus)
        
        # Option A (Windowed Batch - Current Code)
        pk_a, wd_a, f1_a = 0.0, 0.0, 0.0
        # Option B (True Streaming)
        pk_b, wd_b, f1_b = 0.0, 0.0, 0.0

        for sample in result.samples:
            utts = sample.utterances
            ref = sample.segment_sizes
            ref_bin = segments_to_binary(ref)
            n = len(utts)

            # --- OPTION A ---
            from src.service.sliding_text_tiling import SlidingTextTilingService
            service_a = SlidingTextTilingService(config=config)
            events_a = service_a.process(utts)
            seg_a = [e.utterances_end - e.utterances_start + 1 for e in events_a]
            b_a = [e.boundary_index for e in events_a]
            bin_a = boundaries_to_binary(b_a, n)

            pk_a += float(segeval.pk(seg_a, ref))
            wd_a += float(segeval.window_diff(seg_a, ref))
            f1_a += float(f1_score(bin_a, ref_bin, labels=[0, 1], average='macro'))

            # --- OPTION B ---
            seg_b_obj = StreamingTextTilingSegmenter(config=config, stopwords=stopwords, lookahead=20)
            seg_b_obj.reset()
            for u in utts:
                seg_b_obj.update(u)
            seg_b_obj.flush()

            b_b = sorted(set(seg_b_obj.committed_boundaries))
            # Convert boundary indices to segment sizes
            sizes_b = []
            prev = -1
            for b in b_b:
                sizes_b.append(b - prev)
                prev = b

            bin_b = boundaries_to_binary(b_b, n)

            pk_b += float(segeval.pk(sizes_b, ref))
            wd_b += float(segeval.window_diff(sizes_b, ref))
            f1_b += float(f1_score(bin_b, ref_bin, labels=[0, 1], average='macro'))

        m = len(result.samples)
        print(f"\nCorpus: {corpus.value}")
        print(f"  Option A (Windowed Batch): Pk = {pk_a/m:.4f}, WD = {wd_a/m:.4f}, F1 = {f1_a/m:.4f}")
        print(f"  Option B (True Streaming):  Pk = {pk_b/m:.4f}, WD = {wd_b/m:.4f}, F1 = {f1_b/m:.4f}")
        print(f"  Delta (B - A):            Pk = {(pk_b-pk_a)/m:+.4f}, WD = {(wd_b-wd_a)/m:+.4f}, F1 = {(f1_b-f1_a)/m:+.4f}")


if __name__ == "__main__":
    run_evaluation()
