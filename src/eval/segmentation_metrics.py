"""Segmentation metrics: P_k (Beeferman 1999), Win-Diff (Pevzner 2002), F1 (macro).

P_k and Win-Diff are penalty metrics (lower = better); F1 is harmonic mean
(higher = better). All three are standard for dialogue topic segmentation
(paper-1 §4.3).
"""

from __future__ import annotations

import numpy as np


def pk(predicted: list[int], true: list[int], window: int | None = None) -> float:
    """Tính chỉ số chỉ số chỉ số chỉ số độ lỗi P_k (Beeferman et al., 1999) giữa ranh giới dự đoán và thực tế."""
    n = _total(predicted, true)
    if n < 2:
        return 0.0
    if window is None:
        window = max(1, _median_segment_length(true) // 2)
    n = max(n, 2 * window + 1)
    # Build boundary sets
    pred_set = _to_boundary_set(predicted, n)
    true_set = _to_boundary_set(true, n)

    mismatches = 0
    for i in range(n - window):
        a = pred_set[i] != pred_set[i + window]
        b = true_set[i] != true_set[i + window]
        if a != b:
            mismatches += 1
    return mismatches / (n - window)


def win_diff(predicted: list[int], true: list[int], window: int | None = None) -> float:
    """Tính chỉ số độ lỗi Win-Diff (Pevzner and Hearst, 2002)."""
    n = _total(predicted, true)
    if n < 2:
        return 0.0
    if window is None:
        window = max(1, _median_segment_length(true) // 2)
    n = max(n, 2 * window + 1)
    pred_set = _to_boundary_set(predicted, n)
    true_set = _to_boundary_set(true, n)
    mismatches = 0
    for i in range(n - window):
        pred_boundaries = sum(pred_set[i : i + window])
        true_boundaries = sum(true_set[i : i + window])
        if pred_boundaries != true_boundaries:
            mismatches += 1
    return mismatches / (n - window)


def f1_score(predicted: list[int], true: list[int]) -> float:
    """Tính điểm F1-score ở cấp độ phân đoạn giữa dự đoán và nhãn chuẩn."""
    if not predicted or not true:
        return 0.0
    n = _total(predicted, true)
    pred_segs = _segments_from_ends(predicted, n)
    true_segs = _segments_from_ends(true, n)
    true_set = set(true_segs)
    pred_set = set(pred_segs)
    tp = len(pred_set & true_set)
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(true_set) if true_set else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _to_boundary_set(ends: list[int], n: int) -> list[int]:
    """Chuyển đổi danh sách ranh giới kết thúc phân đoạn thành mảng nhị phân 0/1 độ dài n."""
    out = [0] * n
    for e in ends:
        if 0 <= e < n:
            out[e] = 1
    return out


def _segments_from_ends(ends: list[int], n: int | None = None) -> list[tuple[int, int]]:
    """Chuyển đổi các chỉ số ranh giới kết thúc thành danh sách các cặp (bắt đầu, kết thúc)."""
    if not ends:
        return []
    result: list[tuple[int, int]] = []
    prev = 0
    for e in ends:
        result.append((prev, e))
        prev = e + 1
    if n is not None and prev < n:
        result.append((prev, n - 1))
    return result


def _median_segment_length(ends: list[int]) -> int:
    """Tính độ dài trung vị của các phân đoạn từ danh sách chỉ số ranh giới kết thúc."""
    segs = _segments_from_ends(ends)
    if not segs:
        return 1
    sizes = [e - s + 1 for s, e in segs]
    return int(np.median(sizes))


def _total(predicted: list[int], true: list[int]) -> int:
    """Tính tổng số câu thoại từ danh sách nhãn ranh giới chuẩn."""
    return (max(true) + 1) if true else 0
