"""Repository layer: model loaders and file IO.

Public API:
    ModelLoader         -- per-process singleton for local seq2seq caching
    ModelHandle         -- frozen record of a loaded model + its provenance
    ModelKind           -- enum of cacheable model identifiers
    TranscriptRepo      -- reads data/eval_vi JSON into DialogueTranscript
    TranscriptRepoError -- typed error for transcript IO failures
    RecapRepo           -- round-trips HierarchicalRecap as JSON
    RecapRepoError      -- typed error for recap IO failures
    RepoIOError         -- typed error for the shared _io helper
    SUMMARY_PREFIX_VI, TITLE_PREFIX_VI -- exact fine-tuning prefixes
"""

from __future__ import annotations

from ._io import RepoIOError, read_json_file, write_json_file
from .model_loader import (
    CHUNK_SUMMARIZER_PATH, TOPIC_TITLER_PATH, ModelHandle, ModelKind,
    ModelLoadError, ModelLoader,
)
from .recap_repo import RecapRepo, RecapRepoError
from .prompts_vi import SUMMARY_PREFIX_VI, TITLE_PREFIX_VI
from .seq2seq_inference import (
    BARTphoTopicTitler,
    ChunkSummarizer,
    GenerationError,
    TopicTitler,
    ViT5ChunkSummarizer,
)
from .transcript_repo import TranscriptRepo, TranscriptRepoError

__all__ = [
    "ModelLoader",
    "ModelHandle",
    "ModelKind",
    "ModelLoadError",
    "CHUNK_SUMMARIZER_PATH",
    "TOPIC_TITLER_PATH",
    "ChunkSummarizer",
    "TopicTitler",
    "ViT5ChunkSummarizer",
    "BARTphoTopicTitler",
    "GenerationError",
    "SUMMARY_PREFIX_VI",
    "TITLE_PREFIX_VI",
    "TranscriptRepo",
    "TranscriptRepoError",
    "RecapRepo",
    "RecapRepoError",
    "RepoIOError",
    "read_json_file",
    "write_json_file",
]
