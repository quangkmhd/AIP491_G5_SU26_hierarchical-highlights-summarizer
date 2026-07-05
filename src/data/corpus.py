"""Corpus enum + metadata for the 6 evaluation corpora."""

from __future__ import annotations

from enum import Enum


class Corpus(str, Enum):
    """Catalog of evaluation corpora shipped in data/eval_vi/."""

    DIALSEG_711 = "dialseg_711"
    DOC2DIAL = "doc2dial"
    MEETING_AMI = "meeting_ami"
    MEETING_COMMITTEE = "meeting_committee"
    MEETING_ICSI = "meeting_icsi"
    TIAGE = "tiage"


# Per-corpus metadata. avg_turns is computed once from the corpus file
# and cached here; if the corpus file changes, recompute and update.
CORPUS_METADATA: dict[Corpus, dict[str, str | int]] = {
    Corpus.DIALSEG_711: {
        "language": "en",
        "source": "DialSeg_711 (Xu et al., 2021) -- task-oriented English dialogues",
        "domain": "task-oriented",
    },
    Corpus.DOC2DIAL: {
        "language": "en",
        "source": "Doc2Dial (Feng et al., 2020) -- document-grounded English dialogues",
        "domain": "task-oriented",
    },
    Corpus.MEETING_AMI: {
        "language": "en",
        "source": "AMI meeting corpus (Carletta et al., 2005) -- English meetings",
        "domain": "meeting",
    },
    Corpus.MEETING_COMMITTEE: {
        "language": "vi",
        "source": "Vietnamese committee meeting sample (project-internal)",
        "domain": "meeting",
    },
    Corpus.MEETING_ICSI: {
        "language": "en",
        "source": "ICSI meeting corpus (Janin et al., 2003) -- English meetings",
        "domain": "meeting",
    },
    Corpus.TIAGE: {
        "language": "en",
        "source": "Tiage (Aly et al., 2021) -- topic-grounded English dialogues",
        "domain": "open-domain",
    },
}


class CorpusMetadata:
    """Read-only metadata for a single corpus."""

    def __init__(self, corpus: Corpus) -> None:
        self.corpus = corpus
        meta = CORPUS_METADATA[corpus]
        self.language: str = str(meta["language"])
        self.source: str = str(meta["source"])
        self.domain: str = str(meta["domain"])

    def __repr__(self) -> str:
        return f"CorpusMetadata({self.corpus.value}, lang={self.language}, domain={self.domain})"
