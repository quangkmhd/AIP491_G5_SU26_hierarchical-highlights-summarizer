"""Segmenter module — pure-algorithm topic segmentation with no external scoring model.

The sliding-texttiling segmenter works entirely on lexical BoW similarity
and multi-scale depth scoring. The wrapping service that emits SegmentEvents
lives in `src/service/text_tiling.py`.

Public API:
    similarity_scores, multiscale_depth, merge_small_segments,
    find_boundaries, normalize, cosine, DEFAULT_RADII

`depth_scores` is intentionally not re-exported: it is an internal helper
of `multiscale_depth` whose radius-clamped peak search only makes sense
in the multi-scale aggregation context. Callers that need raw depths
should use `multiscale_depth` instead.
"""

from .sliding_texttiling import (
    bow,
    cosine,
    DEFAULT_RADII,
    find_boundaries,
    merge_small_segments,
    multiscale_depth,
    normalize,
    similarity_scores,
)

__all__ = [
    "DEFAULT_RADII",
    "bow",
    "cosine",
    "find_boundaries",
    "merge_small_segments",
    "multiscale_depth",
    "normalize",
    "similarity_scores",
]