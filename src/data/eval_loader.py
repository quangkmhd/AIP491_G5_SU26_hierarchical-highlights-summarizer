"""EvalLoader -- load every JSON file in data/eval_vi/ as a list of DialogueSample."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .corpus import Corpus, CorpusMetadata
from .dialogue_sample import DialogueSample


class DataLoaderError(ValueError):
    """Raised when an evaluation corpus file is malformed or missing."""


@dataclass(frozen=True)
class LoadResult:
    """One corpus's load result: metadata + samples + counts."""

    corpus: Corpus
    metadata: CorpusMetadata
    samples: tuple[DialogueSample, ...]
    train_count: int
    dev_count: int
    test_count: int

    @property
    def total(self) -> int:
        return len(self.samples)


class EvalLoader:
    """Loads every JSON file in data/eval_vi/ as a list of DialogueSample.

    Usage:
        loader = EvalLoader(Path("data/eval_vi"))
        result = loader.load(Corpus.MEETING_COMMITTEE)
        for sample in result.samples:
            print(sample.dial_id, sample.utterance_count, sample.segment_sizes)
    """

    CORPUS_TO_FILENAME: dict[Corpus, str] = {
        Corpus.DIALSEG_711: "dialseg_711.json",
        Corpus.DOC2DIAL: "doc2dial.json",
        Corpus.MEETING_AMI: "meeting_ami.json",
        Corpus.MEETING_COMMITTEE: "meeting_committee.json",
        Corpus.MEETING_ICSI: "meeting_icsi.json",
        Corpus.TIAGE: "tiage.json",
    }

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        if not self.root.is_dir():
            raise DataLoaderError(f"Data root not found: {self.root}")

    def load(self, corpus: Corpus) -> LoadResult:
        """Load one corpus. Raises DataLoaderError on parse failure."""
        filename = self.CORPUS_TO_FILENAME[corpus]
        path = self.root / filename
        if not path.is_file():
            raise DataLoaderError(f"Corpus file not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as e:
            raise DataLoaderError(f"Malformed JSON in {path}: {e}") from e
        if not isinstance(raw, list):
            raise DataLoaderError(
                f"{path} must contain a JSON array, got {type(raw).__name__}"
            )

        samples: list[DialogueSample] = []
        for idx, item in enumerate(raw):
            try:
                samples.append(DialogueSample.model_validate(item))
            except Exception as e:
                raise DataLoaderError(
                    f"{path} sample #{idx} failed validation: {e}"
                ) from e

        train_count = sum(1 for s in samples if s.set == "train")
        dev_count = sum(1 for s in samples if s.set == "dev")
        test_count = sum(1 for s in samples if s.set == "test")

        return LoadResult(
            corpus=corpus,
            metadata=CorpusMetadata(corpus),
            samples=tuple(samples),
            train_count=train_count,
            dev_count=dev_count,
            test_count=test_count,
        )

    def load_all(self) -> Iterator[LoadResult]:
        """Yield LoadResult for every known corpus. Raises on first missing/malformed file."""
        for corpus in Corpus:
            yield self.load(corpus)
