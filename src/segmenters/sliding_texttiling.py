"""Sliding TextTiling segmenter (no scoring model needed).

Multi-scale BoW cosine similarity with sliding-window depth scoring.
Adapted from /16-eval-DTS/segmenters/sliding_texttiling.py for the
service layer used by the meeting-recap orchestrator. This module holds
the pure algorithm; the wrapping service lives in
`src/service/text_tiling.py` so that pipeline-level concerns
(SegmentEvent emission, logging, state reset) stay close to the
orchestrator.
"""

from __future__ import annotations

import math

import numpy as np


# Default parameters match the reference implementation in 16-eval-DTS.
DEFAULT_RADII: list[int] = [3, 5, 10, 15, 20]


def bow(text: str, stopwords: set[str]) -> dict[str, int]:
    """Lowercase word counts, stop-word filtered.

    `stopwords` must be supplied by the caller; this module intentionally
    avoids any third-party stopword-loading dependency so callers can
    plug in token sets from any language or no filtering at all.
    """
    words = [w.strip(".,!?\"'()[]:;-") for w in text.lower().split()]
    words = [w for w in words if w and w not in stopwords]
    out: dict[str, int] = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    return out


def cosine(a: dict[str, int], b: dict[str, int]) -> float:
    """Cosine similarity of two BoW dicts."""
    inter = set(a) & set(b)
    num = sum(a[w] * b[w] for w in inter)
    den = math.sqrt(sum(v ** 2 for v in a.values())) * math.sqrt(sum(v ** 2 for v in b.values()))
    return num / den if den else 0.0


def similarity_scores(
    utterances: list[str],
    block_size: int,
    stopwords: set[str],
) -> list[float]:
    """BoW cosine similarity for n-1 consecutive gaps, pooling each side
    of every gap into a `block_size` window."""
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
    """Depth at index i = 0.5 * (hl + hr - 2 * s[i]).

    `hl`/`hr` are the first peak reached on each side of i within `radius`.
    If `radius` is None the search runs to the array edges (full depth).
    """
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
    """Per-radius normalization so depths from different scales are comparable."""
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
    """Stack depth profiles from every radius, normalize each, then aggregate.

    `radii` must be a non-empty list of positive integers — guaranteed by
    `SlidingTextTilingConfig._radii_non_empty` and by the substitution of
    `DEFAULT_RADII` inside `find_boundaries` when the caller passes None.
    """
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
    """Greedy post-pass: drop the smallest segment until every segment is
    at least `min_seg` long, preferring the side with the shallower depth."""
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
    block_size: int = 3,
    radii: list[int] | None = None,
    alpha: float = 0.9,
    stopwords: set[str] | None = None,
    agg: str = "mean",
    normalize_mode: str = "zscore",
    min_segment_ratio: float = 0.08,
) -> tuple[list[int], dict[int, float]]:
    """Run the full sliding-TextTiling pipeline and return boundary indices.

    The final boundary (n-1) is always appended as a force-close so the
    tail segment is emitted. Returns (sorted_boundary_indices, depth_at_boundary).
    """
    n = len(utterances)
    if n <= 1:
        return [n - 1] if n == 1 else [], {}
    radii = list(radii) if radii is not None else list(DEFAULT_RADII)
    sw = stopwords if stopwords is not None else set()

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
