"""Data layer -- multi-corpus evaluation data loaders.

Independent of config/repo/service/runtime/ui. Pure data loading only.
"""

from .corpus import Corpus, CorpusMetadata
from .dialogue_sample import DialogueSample
from .eval_loader import EvalLoader, LoadResult

__all__ = [
    "Corpus",
    "CorpusMetadata",
    "DialogueSample",
    "EvalLoader",
    "LoadResult",
]
