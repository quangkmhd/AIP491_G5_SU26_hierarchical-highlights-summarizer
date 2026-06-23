import json
import re
from typing import Any


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_json_response(raw_response: str) -> Any:
    stripped = strip_json_fence(raw_response)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    repaired = repair_common_json_glitches(stripped)
    if repaired != stripped:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            stripped = repaired
    for candidate in balanced_json_candidates(stripped):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    object_start = stripped.find("{")
    object_end = stripped.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        try:
            return json.loads(stripped[object_start : object_end + 1])
        except json.JSONDecodeError:
            pass
    array_start = stripped.find("[")
    array_end = stripped.rfind("]")
    if array_start != -1 and array_end != -1 and array_end > array_start:
        try:
            return json.loads(stripped[array_start : array_end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError("Model response did not contain parseable JSON")


def repair_common_json_glitches(text: str) -> str:
    return re.sub(
        r'("[^"]+"\s*:\s*)\[[^\[\]\{\}"]{1,80}\]"\s*:\s*\[',
        r"\1[",
        text,
    )


def balanced_json_candidates(text: str) -> list[str]:
    candidates = []
    start_chars = {"{": "}", "[": "]"}
    for start_index, char in enumerate(text):
        if char not in start_chars:
            continue
        stack = [start_chars[char]]
        in_string = False
        escaped = False
        for index in range(start_index + 1, len(text)):
            current = text[index]
            if escaped:
                escaped = False
                continue
            if current == "\\":
                escaped = True
                continue
            if current == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if current in start_chars:
                stack.append(start_chars[current])
                continue
            if stack and current == stack[-1]:
                stack.pop()
                if not stack:
                    candidates.append(text[start_index : index + 1])
                    break
    return candidates

