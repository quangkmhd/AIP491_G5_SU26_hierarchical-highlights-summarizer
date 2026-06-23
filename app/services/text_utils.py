import math
import re
import statistics
import unicodedata
from collections import Counter
from functools import lru_cache
from typing import Any

import stopwordsiso


TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\ufeff", "").split())


def estimate_tokens(text: str) -> int:
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    return max(1, int(math.ceil(len(words) * 1.33)))


def chunked_sequence(items: list[Any], batch_size: int) -> list[list[Any]]:
    if not items:
        return []
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


@lru_cache(maxsize=1)
def multilingual_stopwords() -> frozenset[str]:
    words = stopwordsiso.stopwords(sorted(stopwordsiso.langs()))
    return frozenset(
        normalized
        for word in words
        if len(normalized := normalize_token(word)) >= 2
    )


def normalize_token(token: str) -> str:
    folded = unicodedata.normalize("NFKC", str(token).casefold())
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFD", folded)
        if not unicodedata.combining(char)
    )
    return unicodedata.normalize("NFC", without_accents)


def tokenize_for_similarity(text: str) -> list[str]:
    stopwords = multilingual_stopwords()
    tokens = []
    for raw_token in TOKEN_RE.findall(text):
        token = normalize_token(raw_token)
        if len(token) < 2 or token in stopwords:
            continue
        tokens.append(token)
    return tokens


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def depth_threshold(depth_scores: list[float]) -> float:
    if not depth_scores:
        return 1.0
    spread = statistics.pstdev(depth_scores) * 0.25 if len(depth_scores) > 1 else 0.0
    return max(0.35, statistics.mean(depth_scores) + spread)
