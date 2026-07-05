"""Repository layer: model loaders and file IO.

Public API:
    ModelLoader         -- per-process singleton for HF model + 4-bit LLM caching
    ModelHandle         -- frozen record of a loaded model + its provenance
    ModelKind           -- enum of cacheable model identifiers
    MockLLMBackbone     -- offline stand-in for the Vietnamese LLM
    CoherenceNet        -- paper-1 NSP-BERT coherence scorer
    _coerce_token_ids   -- clamp token IDs to the model's embedding vocab
    TranscriptRepo      -- reads data/eval_vi JSON into DialogueTranscript
    TranscriptRepoError -- typed error for transcript IO failures
    RecapRepo           -- round-trips HierarchicalRecap as JSON
    RecapRepoError      -- typed error for recap IO failures
    RepoIOError         -- typed error for the shared _io helper
    LLMTask, get_prompt -- Vietnamese prompt registry
    NSP_CKPT_PATH       -- absolute path to the pre-trained NSP checkpoint
"""

from __future__ import annotations

from ._io import RepoIOError, read_json_file, write_json_file
from .coherence_net import CoherenceNet, NSP_CKPT_PATH
from .model_loader import (
    LLM_BACKBONE_ID,
    MockLLMBackbone,
    ModelHandle,
    ModelKind,
    ModelLoader,
    NSP_ENCODER_ID,
    _coerce_token_ids,
)
from .prompts_vi import (
    HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
    HIERARCHIC_TITLE_PROMPT_VI,
    LLMTask,
    SSDST_ABSTRACTIVE_PROMPT_VI,
    SSDST_STATE_UPDATE_PROMPT_VI,
    SYSTEM_PROMPT_VI,
    get_prompt,
)
from .recap_repo import RecapRepo, RecapRepoError
from .transcript_repo import TranscriptRepo, TranscriptRepoError

__all__ = [
    "CoherenceNet",
    "NSP_CKPT_PATH",
    "ModelLoader",
    "ModelHandle",
    "ModelKind",
    "MockLLMBackbone",
    "LLM_BACKBONE_ID",
    "NSP_ENCODER_ID",
    "_coerce_token_ids",
    "TranscriptRepo",
    "TranscriptRepoError",
    "RecapRepo",
    "RecapRepoError",
    "RepoIOError",
    "read_json_file",
    "write_json_file",
    "LLMTask",
    "get_prompt",
    "SYSTEM_PROMPT_VI",
    "HIERARCHIC_ABSTRACTIVE_PROMPT_VI",
    "HIERARCHIC_TITLE_PROMPT_VI",
    "SSDST_ABSTRACTIVE_PROMPT_VI",
    "SSDST_STATE_UPDATE_PROMPT_VI",
]
