import re
from dataclasses import dataclass
from typing import Any

from app.services.text_utils import clean_text, estimate_tokens


@dataclass(frozen=True)
class Utterance:
    index: int
    speaker: str
    start_time: str
    end_time: str
    text: str


def parse_transcript(text: str) -> list[Utterance]:
    header_re = re.compile(
        r"^(?P<speaker>[^:\(\n]+?)(?:\s*\((?P<start>\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(?P<end>\d{1,2}:\d{2}(?::\d{2})?)\))?\s*:\s*(?P<inline>.*)$"
    )
    utterances: list[Utterance] = []
    current_header: tuple[str, str, str] | None = None
    current_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_header, current_lines
        if not current_header:
            current_lines = []
            return
        text_value = clean_text(" ".join(current_lines))
        if text_value:
            speaker, start_time, end_time = current_header
            utterances.append(Utterance(len(utterances) + 1, clean_text(speaker), start_time, end_time, text_value))
        current_header = None
        current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = header_re.match(line)
        if match:
            flush_current()
            start_val = match.group("start")
            end_val = match.group("end")
            current_header = (
                match.group("speaker").strip(),
                start_val.strip() if start_val else "",
                end_val.strip() if end_val else "",
            )
            inline = match.group("inline").strip()
            current_lines = [inline] if inline else []
            continue
        if current_header:
            current_lines.append(line)
        else:
            utterances.append(Utterance(len(utterances) + 1, "Unknown", "", "", clean_text(line)))
    flush_current()
    return utterances


def utterance_to_dict(utterance: Utterance) -> dict[str, Any]:
    return {
        "id": utterance.index,
        "speaker": utterance.speaker,
        "start_time": utterance.start_time,
        "end_time": utterance.end_time,
        "text": utterance.text,
    }


def utterance_by_id(utterances: list[Utterance]) -> dict[int, Utterance]:
    return {utterance.index: utterance for utterance in utterances}


def format_utterance(utterance: Utterance) -> str:
    timespan = f"{utterance.start_time}-{utterance.end_time}" if utterance.start_time or utterance.end_time else "no-time"
    return f"U{utterance.index} [{timespan}] {utterance.speaker}: {utterance.text}"


def format_utterances(utterances: list[Utterance], max_chars: int = 32000) -> str:
    rendered = "\n".join(format_utterance(utterance) for utterance in utterances)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[:max_chars] + "\n...[truncated for prompt budget]"


def context_for_utterance(
    utterances: list[Utterance],
    utterance_id: int,
    before: int = 3,
    after: int = 3,
) -> list[dict[str, Any]]:
    index = max(0, utterance_id - 1)
    start = max(0, index - before)
    end = min(len(utterances), index + after + 1)
    return [utterance_to_dict(utterance) for utterance in utterances[start:end]]


def abstract_context_for_utterance(utterances: list[Utterance], utterance_id: int, token_budget: int) -> list[dict[str, Any]]:
    index = max(0, utterance_id - 1)
    selected = [utterances[index]]
    left = index - 1
    right = index + 1
    while estimate_tokens(" ".join(item.text for item in selected)) < token_budget and (left >= 0 or right < len(utterances)):
        if left >= 0:
            selected.insert(0, utterances[left])
            left -= 1
        if estimate_tokens(" ".join(item.text for item in selected)) >= token_budget:
            break
        if right < len(utterances):
            selected.append(utterances[right])
            right += 1
    return [utterance_to_dict(utterance) for utterance in selected]

