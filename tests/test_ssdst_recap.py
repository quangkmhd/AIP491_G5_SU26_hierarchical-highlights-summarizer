import unittest
from typing import Any

from app.methods import ssdst_recap as ssdst
from app.methods.ssdst_recap import SsDstRecapMethod
from app.services.model_targets import ModelTarget
from app.services.transcript_parser import Utterance


def make_utterances(texts: list[str]) -> list[Utterance]:
    return [
        Utterance(
            index=index,
            speaker=f"Speaker {index}",
            start_time=f"00:{index:02d}",
            end_time=f"00:{index + 1:02d}",
            text=text,
        )
        for index, text in enumerate(texts, start=1)
    ]


class StatefulMockRunner:
    """Mock runner that records calls and returns deterministic SS-DST outputs.

    - For ``ssdst_abstractive``: returns a chunk note echoing the chunk_id and a
      marker that the belief state was visible in the prompt.
    - For ``ssdst_state_update``: returns a belief state that grows with each
      chunk, proving state is threaded sequentially.
    - For ``hierarchical_title``: returns a minimal title.
    """

    retry_attempts = 1

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._state_call_index = 0

    def complete_json_for_all(
        self,
        task_name: str,
        prompt: str,
        *,
        targets: list[ModelTarget],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "task_name": task_name,
                "prompt": prompt,
                "targets": list(targets),
                "max_tokens": max_tokens,
            }
        )
        target_model = targets[0].model if targets else ""
        parsed: dict[str, Any]
        if task_name == "hierarchical_title":
            parsed = {"title": "Test chapter", "one_line_summary": "Tóm tắt chapter."}
        elif task_name == "ssdst_abstractive":
            # Echo whether the belief state block is present in the prompt.
            state_visible = "Dialogue belief state" in prompt and "current_topic" in prompt
            # Extract chunk_id from the prompt's required chunk ids is fragile; use a counter.
            parsed = {
                "notes": [
                    {
                        "chunk_id": self._current_chunk_id(prompt),
                        "summary": f"note state_visible={state_visible}",
                        "contains_key_point": True,
                        "contains_action_item": False,
                    }
                ]
            }
        elif task_name == "ssdst_state_update":
            self._state_call_index += 1
            parsed = {
                "current_topic": f"topic-{self._state_call_index}",
                "entities": [f"entity-{self._state_call_index}"],
                "decisions": [f"decision-{self._state_call_index}"],
                "open_actions": [f"action-{self._state_call_index}"],
                "resolved_references": [{"pronoun": "nó", "refers_to": f"ref-{self._state_call_index}"}],
            }
        else:
            parsed = {}
        return [
            {
                "task": task_name,
                "target": target_model,
                "model": target_model,
                "parsed": parsed,
                "raw_preview": "{}",
                "error": "",
                "attempts": 1,
                "duration_seconds": 0,
            }
        ]

    def _current_chunk_id(self, prompt: str) -> str:
        # The prompt embeds required chunk_ids as a JSON array; pull the first one.
        import re

        match = re.search(r'"(chunk-\d+-\d+)"', prompt)
        return match.group(1) if match else "chunk-unknown"


class SsDstRecapTests(unittest.TestCase):
    def test_method_name_and_paper_mapping(self) -> None:
        method = SsDstRecapMethod()
        self.assertEqual(method.name, "ssdst")

    def test_sequential_state_threading_produces_belief_state_trace(self) -> None:
        # 24 utterances -> with CHUNK_UTTERANCES=8 and the small-meeting path,
        # force a single chapter with 3 chunks so we can observe 3 state steps.
        texts = [f"Nội dung utterance số {i}." for i in range(1, 25)]
        utterances = make_utterances(texts)
        runner = StatefulMockRunner()
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        result = SsDstRecapMethod().summarize(utterances, runner, [target], "meeting.md")

        self.assertEqual(result["method"], "ssdst")
        self.assertIn("chapters", result)
        self.assertGreaterEqual(len(result["chapters"]), 1)
        chapter = result["chapters"][0]
        self.assertIn("belief_state_trace", chapter)
        self.assertIn("final_belief_state", chapter)

        # The belief state trace should have one entry per chunk in the chapter.
        chunks = chapter["chunks"]
        trace = chapter["belief_state_trace"]
        self.assertEqual(len(trace), len(chunks))
        # State evolves: each step has a distinct current_topic.
        topics = [entry["state"]["current_topic"] for entry in trace]
        self.assertEqual(topics, [f"topic-{i}" for i in range(1, len(chunks) + 1)])

    def test_belief_state_is_injected_into_abstractive_prompts(self) -> None:
        texts = [f"Utterance {i}." for i in range(1, 17)]
        utterances = make_utterances(texts)
        runner = StatefulMockRunner()
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        SsDstRecapMethod().summarize(utterances, runner, [target], "meeting.md")

        abstractive_calls = [c for c in runner.calls if c["task_name"] == "ssdst_abstractive"]
        self.assertGreaterEqual(len(abstractive_calls), 1)
        # Every abstractive prompt must contain the belief-state block.
        for call in abstractive_calls:
            self.assertIn("Dialogue belief state", call["prompt"])
            self.assertIn("current_topic", call["prompt"])

    def test_state_update_called_once_per_chunk(self) -> None:
        texts = [f"Utterance {i}." for i in range(1, 25)]
        utterances = make_utterances(texts)
        runner = StatefulMockRunner()
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        result = SsDstRecapMethod().summarize(utterances, runner, [target], "meeting.md")
        total_chunks = sum(len(ch["chunks"]) for ch in result["chapters"])
        state_calls = [c for c in runner.calls if c["task_name"] == "ssdst_state_update"]
        self.assertEqual(len(state_calls), total_chunks)

    def test_empty_belief_state_is_well_formed(self) -> None:
        state = dict(ssdst.EMPTY_BELIEF_STATE)
        self.assertEqual(state["entities"], [])
        self.assertEqual(state["decisions"], [])
        self.assertEqual(state["open_actions"], [])
        self.assertEqual(state["resolved_references"], [])
        self.assertEqual(state["current_topic"], "")

    def test_normalize_belief_state_handles_messy_input(self) -> None:
        normalized = ssdst.normalize_belief_state(
            {
                "current_topic": "  kiến trúc mới  ",
                "entities": ["API", "", "  frontend  "],
                "decisions": ["chốt pipeline"],
                "open_actions": ["viết test"],
                "resolved_references": [
                    {"pronoun": "nó", "refers_to": "pipeline"},
                    {"pronoun": "", "refers_to": ""},
                    "not-a-dict",
                ],
            }
        )
        self.assertEqual(normalized["current_topic"], "kiến trúc mới")
        self.assertEqual(normalized["entities"], ["API", "frontend"])
        self.assertEqual(normalized["resolved_references"], [{"pronoun": "nó", "refers_to": "pipeline"}])


if __name__ == "__main__":
    unittest.main()
