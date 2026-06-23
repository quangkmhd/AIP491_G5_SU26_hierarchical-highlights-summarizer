"""Tests for the lexnorm prompt module."""

import json

from app.services.lexnorm.prompt import (
    FEW_SHOT_EXAMPLES,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.services.lexnorm.types_ import Utterance


def _u(idx, text, start="0:00", end="0:01"):
    return Utterance(index=idx, speaker=f"Speaker_{idx:03d}", start_time=start, end_time=end, text=text)


def test_system_prompt_contains_seven_safety_rules():
    """Each rule must be present as a numbered item 1-7 in the prompt.

    Keywords are matched as substrings of each numbered rule line so the
    prompt can be edited (e.g. add clarifications) without breaking the test.
    """
    lines = SYSTEM_PROMPT.splitlines()
    rule_lines = [line for line in lines if len(line) > 2 and line[0].isdigit() and line[1] == "."]
    assert len(rule_lines) >= 7, f"expected at least 7 numbered rules, got {len(rule_lines)}"

    keywords = [
        "substring",        # rule 1: error_words must be substrings
        "paraphr",          # rule 2: no paraphrase
        "chuc nang",        # rule 3: function words must be preserved
        "brand",            # rule 4: no brand guessing
        "viet",             # rule 5: keep Vietnamese forms
        "so luong",         # rule 6: keep numbers/dosages
        "json",             # rule 7: JSON output only
    ]
    for needle in keywords:
        assert any(needle.lower() in line.lower() for line in rule_lines), (
            f"missing safety rule with keyword {needle!r}"
        )


def test_few_shot_examples_parse_as_json_objects():
    assert len(FEW_SHOT_EXAMPLES) >= 3
    for example in FEW_SHOT_EXAMPLES:
        assert "input" in example
        assert "output" in example
        parsed = json.loads(example["output"])
        assert "llm_corrected" in parsed
        assert "error_words" in parsed


def test_build_user_prompt_excludes_truth_field():
    center = _u(5, "CHUNG TA DI LAM")
    ctx = [_u(4, "ROI MINH"), _u(6, "OK")]
    prompt = build_user_prompt(center, ctx)
    assert "ground_truth" not in prompt
    assert "truth_text" not in prompt
    assert "soniox" not in prompt.lower()


def test_build_user_prompt_includes_center_and_context():
    center = _u(10, "TOI DI HOC")
    ctx = [_u(7, "AAA"), _u(8, "BBB"), _u(9, "CCC"), _u(11, "DDD"), _u(12, "EEE")]
    prompt = build_user_prompt(center, ctx)
    assert "TOI DI HOC" in prompt
    for u in ctx:
        assert u.text in prompt
    assert "U10" in prompt


def test_build_user_prompt_handles_empty_context():
    center = _u(1, "XIN CHAO")
    prompt = build_user_prompt(center, [])
    assert "XIN CHAO" in prompt
    assert "U1" in prompt
