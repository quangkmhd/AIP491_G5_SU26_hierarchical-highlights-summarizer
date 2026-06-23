from typing import Any, Protocol

from app.services.completion_client import JsonCompletionRunner
from app.services.model_targets import ModelTarget
from app.services.transcript_parser import Utterance


class RecapMethod(Protocol):
    name: str

    def summarize(
        self,
        utterances: list[Utterance],
        runner: JsonCompletionRunner,
        targets: list[ModelTarget],
        input_name: str,
    ) -> dict[str, Any]:
        ...

