from __future__ import annotations

import math
import numpy as np

DEFAULT_RADII: list[int] = [3, 5, 10, 15, 20]


def bow(text: str, stopwords: set[str]) -> dict[str, int]:
    """Tokenize, lowercase, and count word frequencies after filtering stop-words."""
    words = [w.strip(".,!?\"'()[]:;-") for w in text.lower().split()]
    words = [w for w in words if w and w not in stopwords]
    out: dict[str, int] = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    return out


def cosine(a: dict[str, int], b: dict[str, int]) -> float:
    """Calculate Cosine similarity between two Bag-of-Words dictionaries."""
    inter = set(a) & set(b)
    num = sum(a[w] * b[w] for w in inter)
    den = math.sqrt(sum(v ** 2 for v in a.values())) * math.sqrt(sum(v ** 2 for v in b.values()))
    return num / den if den else 0.0


def similarity_scores(
    utterances: list[str],
    block_size: int,
    stopwords: set[str],
) -> list[float]:
    """Calculate Cosine similarity between consecutive utterance block pairs."""
    bows = [bow(u, stopwords) for u in utterances]
    scores: list[float] = []
    n = len(bows)
    for i in range(n - 1):
        if block_size == 1:
            scores.append(cosine(bows[i], bows[i + 1]))
            continue
        b1: dict[str, int] = {}
        for j in range(max(0, i - block_size + 1), i + 1):
            for w, f in bows[j].items():
                b1[w] = b1.get(w, 0) + f
        b2: dict[str, int] = {}
        for j in range(i + 1, min(n, i + block_size + 1)):
            for w, f in bows[j].items():
                b2[w] = b2.get(w, 0) + f
        scores.append(cosine(b1, b2))
    return scores


def depth_scores(scores: list[float], radius: int | None = None) -> np.ndarray:
    """Calculate depth scores at each gap based on surrounding peak radii."""
    depth: list[float] = []
    n = len(scores)
    for i in range(n):
        lf = rf = scores[i]
        li_start = max(0, i - radius) if radius else i - 1
        for li in range(i - 1, li_start - 1, -1):
            if scores[li] >= lf:
                lf = scores[li]
            else:
                break
        ri_end = min(n - 1, i + radius) if radius else n - 1
        for ri in range(i + 1, ri_end + 1):
            if scores[ri] >= rf:
                rf = scores[ri]
            else:
                break
        depth.append(0.5 * (lf + rf - 2 * scores[i]))
    return np.array(depth)


def normalize(arr: np.ndarray, mode: str) -> np.ndarray:
    """Normalize depth scores using z-score or min-max normalization."""
    if len(arr) == 0:
        return arr
    if mode == "zscore":
        std = arr.std()
        if std > 1e-10:
            return (arr - arr.mean()) / (std + 1e-10)
        return arr - arr.mean()
    if mode == "minmax":
        rng = arr.max() - arr.min()
        if rng > 1e-10:
            return (arr - arr.min()) / (rng + 1e-10)
        return arr - arr.min()
    return arr


def multiscale_depth(
    scores: list[float],
    radii: list[int],
    agg: str = "mean",
    normalize_mode: str = "zscore",
) -> np.ndarray:
    """Aggregate multiscale depth scores across multiple radii."""
    all_depths = [normalize(depth_scores(scores, radius=r), normalize_mode) for r in radii]
    stacked = np.stack(all_depths)
    if agg == "max":
        return stacked.max(axis=0)
    if agg == "sum":
        return stacked.sum(axis=0)
    return stacked.mean(axis=0)


def merge_small_segments(
    boundaries: list[int],
    boundary_depths: dict[int, float],
    min_seg: int,
) -> list[int]:
    """Merge small segments into neighboring segments with smaller depth drops."""
    result = list(boundaries)
    while True:
        sizes: list[int] = []
        prev = -1
        for b in result:
            sizes.append(b - prev)
            prev = b

        min_idx = -1
        min_val = float("inf")
        for i, sz in enumerate(sizes):
            if sz < min_seg and sz < min_val:
                min_val = sz
                min_idx = i
        if min_idx < 0:
            break

        if min_idx == 0:
            if len(result) > 2:
                result.pop(0)
            else:
                break
        elif min_idx == len(sizes) - 1:
            if len(result) > 2:
                result.pop(len(result) - 2)
            else:
                break
        else:
            left_d = boundary_depths.get(result[min_idx - 1], float("inf"))
            right_d = boundary_depths.get(result[min_idx], float("inf"))
            if left_d <= right_d:
                result.pop(min_idx - 1)
            else:
                result.pop(min_idx)
    return result


def find_boundaries(
    utterances: list[str],
    block_size: int = 2,
    radii: list[int] | None = None,
    alpha: float = 1.0,
    stopwords: set[str] | None = None,
    agg: str = "mean",
    normalize_mode: str = "zscore",
    min_segment_ratio: float = 0.08,
    window_size: int = 40,
    stride: int = 5,
) -> tuple[list[int], dict[int, float]]:
    """Execute Sliding TextTiling algorithm to find topic segment boundary positions."""
    n = len(utterances)
    if n <= 1:
        return [n - 1] if n == 1 else [], {}
    radii = list(radii) if radii is not None else list(DEFAULT_RADII)
    sw = stopwords if stopwords is not None else set()

    if n <= window_size:
        sim = similarity_scores(utterances, block_size=block_size, stopwords=sw)
        if len(sim) < 2:
            return [n - 1], {}
        depth = multiscale_depth(sim, radii=radii, agg=agg, normalize_mode=normalize_mode)
        threshold = float(depth.mean() + alpha * depth.std())
        candidates = [(i, float(depth[i])) for i in range(len(depth)) if depth[i] > threshold]
        boundaries = [c[0] for c in candidates]
        boundary_depths = dict(candidates)
        boundaries.append(n - 1)
        boundaries = sorted(set(boundaries))
        min_seg = max(2, int(n * min_segment_ratio))
        if min_seg > 2 and len(boundaries) > 2:
            boundaries = merge_small_segments(boundaries, boundary_depths, min_seg)
        return boundaries, boundary_depths

    starts = []
    curr = 0
    while curr < n - window_size:
        starts.append(curr)
        curr += stride
    if not starts or starts[-1] != n - window_size:
        starts.append(n - window_size)

    gap_to_window = {}
    for g in range(n - 1):
        best_start = None
        min_dist = float("inf")
        for start in starts:
            if start <= g < start + window_size - 1:
                center = start + (window_size - 1) / 2.0
                dist = abs(g - center)
                if dist < min_dist:
                    min_dist = dist
                    best_start = start
        gap_to_window[g] = best_start

    window_gaps = {start: [] for start in starts}
    for g, start in gap_to_window.items():
        if start is not None:
            window_gaps[start].append(g)

    boundaries = []
    boundary_depths = {}

    for start in starts:
        window_utts = utterances[start : start + window_size]
        sim = similarity_scores(window_utts, block_size=block_size, stopwords=sw)
        if len(sim) < 2:
            continue
        depth = multiscale_depth(sim, radii=radii, agg=agg, normalize_mode=normalize_mode)
        threshold = float(depth.mean() + alpha * depth.std())

        for g in window_gaps[start]:
            j = g - start
            if depth[j] > threshold:
                boundaries.append(g)
                boundary_depths[g] = float(depth[j])

    boundaries.append(n - 1)
    boundaries = sorted(set(boundaries))

    min_seg = max(2, int(window_size * min_segment_ratio))
    if min_seg > 2 and len(boundaries) > 2:
        boundaries = merge_small_segments(boundaries, boundary_depths, min_seg)

    return boundaries, boundary_depths


class StreamingTextTilingSegmenter:
    """Sliding window TextTiling streaming segmentation algorithm."""

    def __init__(
        self,
        block_size: int = 2,
        radii: list[int] | None = None,
        alpha: float = 1.2,
        stopwords: set[str] | None = None,
        agg: str = "mean",
        normalize_mode: str = "zscore",
        min_segment_ratio: float = 0.08,
        window_size: int = 40,
        stride: int = 5,
        lookahead: int = 20,
    ) -> None:
        self.block_size = block_size
        self.radii = list(radii) if radii is not None else list(DEFAULT_RADII)
        self.alpha = alpha
        self.stopwords = stopwords if stopwords is not None else set()
        self.agg = agg
        self.normalize_mode = normalize_mode
        self.min_segment_ratio = min_segment_ratio
        self.window_size = window_size
        self.stride = stride
        self.lookahead = lookahead
        self.reset()

    def reset(self) -> None:
        """Reset streaming buffers and segmentation state to initial values."""
        self.buffer: list[str] = []
        self.next_window_start: int = 0
        self.committed_boundaries: list[int] = []
        self.boundary_depths: dict[int, float] = {}
        self.pending_candidates: dict[int, float] = {}
        self.last_committed_index: int = -1

    def update(self, utterance: str) -> list[tuple[int, float]]:
        """Ingest a new utterance, evaluate sliding windows, and return committed boundaries."""
        self.buffer.append(utterance)
        n = len(self.buffer)
        W = self.window_size
        S = self.stride

        newly_committed: list[tuple[int, float]] = []

        while n - self.next_window_start >= W:
            start = self.next_window_start
            win_utts = self.buffer[start : start + W]

            sim = similarity_scores(win_utts, block_size=self.block_size, stopwords=self.stopwords)
            if len(sim) >= 2:
                depth = multiscale_depth(
                    sim,
                    radii=self.radii,
                    agg=self.agg,
                    normalize_mode=self.normalize_mode,
                )
                threshold = float(depth.mean() + self.alpha * depth.std())

                for j in range(len(depth)):
                    g = start + j
                    if g <= self.last_committed_index:
                        continue
                    if depth[j] > threshold:
                        self.pending_candidates[g] = float(depth[j])

            commit_cutoff = start + W - self.lookahead
            eligible = sorted([g for g in self.pending_candidates if g <= commit_cutoff])

            if eligible:
                min_seg = max(2, int(W * self.min_segment_ratio))
                b_list = list(eligible)
                d_map = {g: self.pending_candidates[g] for g in b_list}

                merged = merge_small_segments(b_list, d_map, min_seg)

                for g in merged:
                    if g > self.last_committed_index:
                        depth_val = d_map[g]
                        self.committed_boundaries.append(g)
                        self.boundary_depths[g] = depth_val
                        self.last_committed_index = g
                        newly_committed.append((g, depth_val))
                        if g in self.pending_candidates:
                            del self.pending_candidates[g]

                to_remove = [g for g in self.pending_candidates if g <= commit_cutoff]
                for g in to_remove:
                    del self.pending_candidates[g]

            self.next_window_start += S

        return newly_committed

    def flush(self) -> list[tuple[int, float]]:
        """Flush remaining utterances in tail buffer and commit final meeting boundary."""
        n = len(self.buffer)
        newly_committed: list[tuple[int, float]] = []
        if n == 0:
            return []

        W = self.window_size

        if n <= W:
            sim = similarity_scores(self.buffer, block_size=self.block_size, stopwords=self.stopwords)
            if len(sim) >= 2:
                depth = multiscale_depth(
                    sim,
                    radii=self.radii,
                    agg=self.agg,
                    normalize_mode=self.normalize_mode,
                )
                threshold = float(depth.mean() + self.alpha * depth.std())
                for j in range(len(depth)):
                    if depth[j] > threshold:
                        self.pending_candidates[j] = float(depth[j])
        else:
            start = n - W
            win_utts = self.buffer[start:n]
            sim = similarity_scores(win_utts, block_size=self.block_size, stopwords=self.stopwords)
            if len(sim) >= 2:
                depth = multiscale_depth(
                    sim,
                    radii=self.radii,
                    agg=self.agg,
                    normalize_mode=self.normalize_mode,
                )
                threshold = float(depth.mean() + self.alpha * depth.std())
                for j in range(len(depth)):
                    g = start + j
                    if g > self.last_committed_index and depth[j] > threshold:
                        self.pending_candidates[g] = float(depth[j])

        uncommitted = sorted([g for g in self.pending_candidates if g > self.last_committed_index])
        if uncommitted:
            min_seg = max(2, int(min(n, W) * self.min_segment_ratio))
            d_map = {g: self.pending_candidates[g] for g in uncommitted}
            merged = merge_small_segments(uncommitted, d_map, min_seg)
            for g in merged:
                if g > self.last_committed_index:
                    depth_val = d_map[g]
                    self.committed_boundaries.append(g)
                    self.boundary_depths[g] = depth_val
                    self.last_committed_index = g
                    newly_committed.append((g, depth_val))

        tail_index = n - 1
        if not self.committed_boundaries or self.committed_boundaries[-1] != tail_index:
            self.committed_boundaries.append(tail_index)
            self.boundary_depths[tail_index] = 0.0
            newly_committed.append((tail_index, 0.0))

        return newly_committed


class MultiscaleTextTilingService:
    """MultiscaleTextTilingService topic segmentation service."""

    def __init__(
        self,
        block_size: int = 2,
        radii: list[int] | None = None,
        alpha: float = 1.0,
        use_stopwords: bool = True,
        agg: str = "mean",
        normalize: str = "zscore",
        min_segment_ratio: float = 0.08,
        window_size: int = 40,
        stride: int = 5,
    ) -> None:
        self.block_size = block_size
        self.radii = radii if radii is not None else [3, 5, 10, 15, 20]
        self.alpha = alpha
        self.use_stopwords = use_stopwords
        self.agg = agg
        self.normalize = normalize
        self.min_segment_ratio = min_segment_ratio
        self.window_size = window_size
        self.stride = stride

        if self.use_stopwords:
            import stopwordsiso
            self._stopwords = stopwordsiso.stopwords(["vi"])
        else:
            self._stopwords = set()

        self._streamer = StreamingTextTilingSegmenter(
            block_size=self.block_size,
            radii=self.radii,
            alpha=self.alpha,
            stopwords=self._stopwords,
            agg=self.agg,
            normalize_mode=self.normalize,
            min_segment_ratio=self.min_segment_ratio,
            window_size=self.window_size,
            stride=self.stride,
        )
        self.reset()

    def reset(self) -> None:
        """Reset streaming service state to initial values."""
        self._streamer.reset()
        self._last_emitted_boundary: int = -1

    def update(self, utterance: str) -> list[tuple[int, int]]:
        """Accept a new utterance in streaming mode and return (start, end) segment ranges if committed."""
        committed = self._streamer.update(utterance)
        ranges: list[tuple[int, int]] = []
        for b, _ in committed:
            ranges.append((self._last_emitted_boundary + 1, b))
            self._last_emitted_boundary = b
        return ranges

    def flush(self) -> list[tuple[int, int]]:
        """Flush remaining utterance buffer at the end of a meeting to finalize segment ranges."""
        committed = self._streamer.flush()
        ranges: list[tuple[int, int]] = []
        for b, _ in committed:
            ranges.append((self._last_emitted_boundary + 1, b))
            self._last_emitted_boundary = b
        return ranges

    def process(self, utterances: list[str]) -> list[tuple[int, int]]:
        """Process a list of utterances in batch mode and return segment index ranges (start, end)."""
        self.reset()
        n = len(utterances)
        if n == 0:
            return []
        if n == 1:
            return [(0, 0)]

        boundaries, _ = find_boundaries(
            utterances,
            block_size=self.block_size,
            radii=self.radii,
            alpha=self.alpha,
            stopwords=self._stopwords,
            agg=self.agg,
            normalize_mode=self.normalize,
            min_segment_ratio=self.min_segment_ratio,
            window_size=self.window_size,
            stride=self.stride,
        )

        ranges: list[tuple[int, int]] = []
        prev = -1
        for b in boundaries:
            ranges.append((prev + 1, b))
            prev = b
        return ranges
