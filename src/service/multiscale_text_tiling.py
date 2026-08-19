from __future__ import annotations

import math
import numpy as np

# Default parameters match the reference implementation in 16-eval-DTS.
DEFAULT_RADII: list[int] = [3, 5, 10, 15, 20]


def bow(text: str, stopwords: set[str]) -> dict[str, int]:
    """Tách từ, chuyển về chữ thường và đếm tần suất từ sau khi lọc stop-word."""
    words = [w.strip(".,!?\"'()[]:;-") for w in text.lower().split()]
    words = [w for w in words if w and w not in stopwords]
    out: dict[str, int] = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    return out


def cosine(a: dict[str, int], b: dict[str, int]) -> float:
    """Tính độ tương đồng Cosine giữa hai từ điển Bag-of-Words."""
    inter = set(a) & set(b)
    num = sum(a[w] * b[w] for w in inter)
    den = math.sqrt(sum(v ** 2 for v in a.values())) * math.sqrt(sum(v ** 2 for v in b.values()))
    return num / den if den else 0.0


def similarity_scores(
    utterances: list[str],
    block_size: int,
    stopwords: set[str],
) -> list[float]:
    """Tính độ tương đồng Cosine cho n-1 khoảng trống giữa các khối câu thoại liên tiếp."""
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
    """Tính điểm độ sâu (depth score) tại mỗi khoảng trống theo bán kính đỉnh xung quanh."""
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
    """Chuẩn hóa điểm độ sâu theo từng bán kính (z-score hoặc min-max)."""
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
    """Tổng hợp điểm độ sâu đa tỷ lệ từ nhiều bán kính khác nhau."""
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
    """Gộp các phân đoạn quá nhỏ vào phân đoạn lân cận có độ sâu nông hơn."""
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
    """Chạy thuật toán Sliding TextTiling để tìm danh sách vị trí ranh giới phân đoạn chủ đề."""
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
    """Thuật toán phân đoạn streaming Sliding TextTiling theo cửa sổ trượt."""

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
        """Khởi tạo thuật toán phân đoạn streaming StreamingTextTilingSegmenter."""
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
        """Đặt lại toàn bộ bộ đệm và trạng thái phân đoạn streaming về ban đầu."""
        self.buffer: list[str] = []
        self.next_window_start: int = 0
        self.committed_boundaries: list[int] = []
        self.boundary_depths: dict[int, float] = {}
        self.pending_candidates: dict[int, float] = {}
        self.last_committed_index: int = -1

    def update(self, utterance: str) -> list[tuple[int, float]]:
        """Nạp một câu thoại mới, đánh giá cửa sổ trượt và trả về danh sách ranh giới đã chốt."""
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
        """Xử lý nốt các câu thoại trong bộ đệm đuôi và chốt ranh giới cuối cuộc họp."""
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


class SegmentEvent:
    """Sự kiện phân đoạn chủ đề SegmentEvent do dịch vụ SlidingTextTilingService phát ra."""

    def __init__(
        self,
        segment_id: str,
        utterances_start: int,
        utterances_end: int,
        depth_score: float,
        boundary_index: int,
    ) -> None:
        self.segment_id = segment_id
        self.utterances_start = utterances_start
        self.utterances_end = utterances_end
        self.depth_score = depth_score
        self.boundary_index = boundary_index


class MultiscaleTextTilingService:
    """Dịch vụ phân đoạn chủ đề đa tỷ lệ MultiscaleTextTilingService."""

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
        """Khởi tạo dịch vụ phân đoạn chủ đề MultiscaleTextTilingService."""
        self.block_size = block_size
        self.radii = radii if radii is not None else [3, 5, 10, 15, 20]
        self.alpha = alpha
        self.use_stopwords = use_stopwords
        self.agg = agg
        self.normalize = normalize
        self.min_segment_ratio = min_segment_ratio
        self.window_size = window_size
        self.stride = stride

        self._segment_counter = 0
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

    def _new_segment_id(self) -> str:
        """Sinh mã ID duy nhất cho phân đoạn mới (ví dụ: seg-0, seg-1)."""
        sid = f"seg-{self._segment_counter}"
        self._segment_counter += 1
        return sid

    def reset(self) -> None:
        """Đặt lại trạng thái streaming của dịch vụ về ban đầu."""
        self._segment_counter = 0
        self._streamer.reset()
        self._last_emitted_boundary: int = -1

    def update(self, utterance: str) -> list[SegmentEvent]:
        """Tiếp nhận một câu thoại mới ở chế độ streaming và trả về sự kiện phân đoạn nếu có."""
        committed = self._streamer.update(utterance)
        events: list[SegmentEvent] = []
        for b, d in committed:
            events.append(
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=self._last_emitted_boundary + 1,
                    utterances_end=b,
                    depth_score=d,
                    boundary_index=b,
                )
            )
            self._last_emitted_boundary = b
        return events

    def flush(self) -> list[SegmentEvent]:
        """Xả bộ đệm câu thoại còn lại ở cuối cuộc họp để chốt phân đoạn cuối."""
        committed = self._streamer.flush()
        events: list[SegmentEvent] = []
        for b, d in committed:
            events.append(
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=self._last_emitted_boundary + 1,
                    utterances_end=b,
                    depth_score=d,
                    boundary_index=b,
                )
            )
            self._last_emitted_boundary = b
        return events

    def process(self, utterances: list[str]) -> list[SegmentEvent]:
        """Xử lý danh sách câu thoại dạng batch và xác định ranh giới phân đoạn chủ đề."""
        self.reset()

        n = len(utterances)
        if n == 0:
            return []
        if n == 1:
            return [
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=0,
                    utterances_end=0,
                    depth_score=0.0,
                    boundary_index=0,
                )
            ]

        boundaries, boundary_depths = find_boundaries(
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

        assert boundaries and boundaries[-1] == n - 1, (
            "find_boundaries must append n-1 as the force-close tail"
        )

        events: list[SegmentEvent] = []
        prev = -1
        for b in boundaries:
            depth_score = boundary_depths.get(b, 0.0)
            events.append(
                SegmentEvent(
                    segment_id=self._new_segment_id(),
                    utterances_start=prev + 1,
                    utterances_end=b,
                    depth_score=depth_score,
                    boundary_index=b,
                )
            )
            prev = b
        return events