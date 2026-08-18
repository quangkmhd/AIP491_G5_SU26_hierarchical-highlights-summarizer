from __future__ import annotations

import logging
import re
from pathlib import Path

from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance

from ._io import RepoIOError, read_json_file


class TranscriptRepoError(Exception):
    """Raised when a transcript file cannot be read or parsed."""


# Placeholder tokens like `{vocalsound}`, `{gap}`, `{disfmarker}`.
# Matched as standalone tokens (surrounded by whitespace or at boundaries).
_PLACEHOLDER_PATTERN = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")
logger = logging.getLogger("src.repo.transcript_repo")


class TranscriptRepo:
    """Read `data/eval_vi/*.json` files into `DialogueTranscript` lists."""

    # Field name that holds the Vietnamese text in the source schema.
    _VI_FIELD: str = "utterances_vi"

    def load_all(self, path: str | Path) -> list[DialogueTranscript]:
        """Nạp toàn bộ các cuộc thoại từ file JSON thành danh sách DialogueTranscript."""
        records = self._read_json(path)
        transcripts = [self._build_transcript(rec) for rec in records]
        logger.info(
            "transcripts loaded path=%s records=%d utterances=%d",
            Path(path),
            len(transcripts),
            sum(len(t.utterances) for t in transcripts),
        )
        return transcripts

    def get_by_dial_id(
        self, path: str | Path, dial_id: int
    ) -> DialogueTranscript:
        """Lấy một cuộc thoại duy nhất khớp với dial_id từ file dữ liệu."""
        for t in self.load_all(path):
            if t.metadata.get("dial_id") == str(dial_id):
                logger.debug("transcript found path=%s dial_id=%s utterances=%d", path, dial_id, len(t.utterances))
                return t
        raise TranscriptRepoError(
            f"dial_id={dial_id} not found in {path}"
        )

    # -- internals ------------------------------------------------------------

    def _read_json(self, path: str | Path) -> list[dict]:
        """Đọc và kiểm tra cấu hình danh sách các bản ghi từ file JSON."""
        p = Path(path)
        try:
            data = read_json_file(p)
        except RepoIOError as exc:
            raise TranscriptRepoError(str(exc)) from exc
        if not isinstance(data, list):
            raise TranscriptRepoError(
                f"Expected a list of records in {p}, got {type(data).__name__}"
            )
        logger.debug("transcript json read path=%s records=%d", p, len(data))
        return data

    @staticmethod
    def _strip_inline_placeholders(text: str) -> str:
        """Loại bỏ các ký tự chú thích nội dòng dạng {...} và làm sạch khoảng trắng."""
        cleaned = _PLACEHOLDER_PATTERN.sub(" ", text)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _build_transcript(self, record: dict) -> DialogueTranscript:
        """Chuyển đổi một bản ghi dict thành đối tượng DialogueTranscript hoàn chỉnh."""
        try:
            texts = record[self._VI_FIELD]
            dial_id = record["dial_id"]
        except KeyError as exc:
            raise TranscriptRepoError(
                f"Missing required field {exc} in record {record.get('dial_id')!r}"
            ) from exc

        # Bỏ qua các câu thoại trống hoặc ký tự giữ chỗ, ghi lại chỉ số gốc của từng câu thoại.
        kept_utterances: list[Utterance] = []
        dropped_indices: list[int] = []
        for original_idx, raw in enumerate(texts):
            stripped = self._strip_inline_placeholders(str(raw))
            if not stripped:
                dropped_indices.append(original_idx)
                continue
            kept_utterances.append(
                Utterance(
                    speaker=f"S{original_idx + 1}",
                    text=stripped,
                    index=len(kept_utterances),
                )
            )

        return DialogueTranscript(
            utterances=kept_utterances,
            meeting_title=f"Committee Meeting {dial_id}",
            metadata={
                "dial_id": str(dial_id),
                "set": str(record.get("set", "")),
                "dropped_empty_indices": ",".join(str(i) for i in dropped_indices),
                "original_utterance_count": str(len(texts)),
            },
        )
