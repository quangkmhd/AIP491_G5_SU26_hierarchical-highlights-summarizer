"""Unit tests for ModelLoader singleton + cache + offline mock."""

import os
import threading
import unittest
from unittest import mock

from src.repo.model_loader import (
    LLM_BACKBONE_ID,
    MockLLMBackbone,
    ModelKind,
    ModelLoader,
)
from src.repo.prompts_vi import LLMTask


class TestModelLoaderSingleton(unittest.TestCase):
    def setUp(self) -> None:
        # Reset the singleton between tests.
        ModelLoader.reset_instance()

    def tearDown(self) -> None:
        ModelLoader.reset_instance()

    def test_instance_returns_same_object(self) -> None:
        a = ModelLoader.instance()
        b = ModelLoader.instance()
        self.assertIs(a, b)

    def test_reset_instance_clears_cache(self) -> None:
        a = ModelLoader.instance()
        ModelLoader.reset_instance()
        b = ModelLoader.instance()
        self.assertIsNot(a, b)

    def test_llm_backbone_id(self) -> None:
        self.assertEqual(LLM_BACKBONE_ID, "unsloth/gemma-4-E2B-it-qat-GGUF")

    def test_model_kind_enum_has_only_llm_backbone(self) -> None:
        self.assertEqual({k.name for k in ModelKind}, {"LLM_BACKBONE"})


class TestMockLLMBackbone(unittest.TestCase):
    def test_mock_records_calls(self) -> None:
        mock_llm = MockLLMBackbone()
        out = mock_llm.generate(prompt="Xin chào", task="segment")
        self.assertIsInstance(out, str)
        self.assertEqual(mock_llm.call_count, 1)
        self.assertEqual(mock_llm.last_prompt, "Xin chào")

    def test_mock_handles_all_hierarchical_tasks(self) -> None:
        mock_llm = MockLLMBackbone()
        for task in LLMTask:
            mock_llm.generate(prompt="x", task=task.value)
        self.assertEqual(mock_llm.call_count, 2)


class TestOfflineMode(unittest.TestCase):
    def setUp(self) -> None:
        ModelLoader.reset_instance()

    def tearDown(self) -> None:
        ModelLoader.reset_instance()

    def test_offline_env_returns_mock_llm(self) -> None:
        with mock.patch.dict(os.environ, {"MODEL_LOAD_LLM": "0"}):
            loader = ModelLoader.instance()
            handle = loader.load_llm_backbone()
        self.assertIsInstance(handle.model, MockLLMBackbone)
        self.assertEqual(handle.kind, ModelKind.LLM_BACKBONE)

    def test_offline_llm_load_logs_mode_and_device(self) -> None:
        with mock.patch.dict(os.environ, {"MODEL_LOAD_LLM": "0"}):
            loader = ModelLoader.instance()
            with self.assertLogs("src.repo.model_loader", level="INFO") as logs:
                loader.load_llm_backbone()
        text = "\n".join(logs.output)
        self.assertIn("loading LLM backbone", text)
        self.assertIn("MODEL_LOAD_LLM=0", text)


def _mock_handle() -> "ModelHandle":
    """Build a ModelHandle carrying a MockLLMBackbone."""
    from src.repo.model_loader import ModelHandle
    return ModelHandle(
        kind=ModelKind.LLM_BACKBONE,
        model=MockLLMBackbone(),
        device="cpu",
        checkpoint_path="mock",
    )


class TestCaching(unittest.TestCase):
    def setUp(self) -> None:
        ModelLoader.reset_instance()

    def tearDown(self) -> None:
        ModelLoader.reset_instance()

    def test_llm_handle_cached_on_second_access(self) -> None:
        loader = ModelLoader.instance()
        with mock.patch(
            "src.repo.model_loader._load_llm_backbone",
            return_value=_mock_handle(),
        ) as fresh:
            a = loader.load_llm_backbone()
            b = loader.load_llm_backbone()
        self.assertIs(a, b)
        # Only one underlying load call.
        self.assertEqual(fresh.call_count, 1)

    def test_llm_cache_hit_logs_debug_only(self) -> None:
        loader = ModelLoader.instance()
        with mock.patch(
            "src.repo.model_loader._load_llm_backbone",
            return_value=_mock_handle(),
        ):
            loader.load_llm_backbone()
            with self.assertLogs("src.repo.model_loader", level="DEBUG") as logs:
                loader.load_llm_backbone()
        self.assertIn("model cache hit kind=llm_backbone", "\n".join(logs.output))


class TestModelLoaderConcurrency(unittest.TestCase):
    """C3: concurrent first-call must not load the model twice."""

    def setUp(self) -> None:
        ModelLoader.reset_instance()

    def tearDown(self) -> None:
        ModelLoader.reset_instance()

    def test_concurrent_first_call_loads_llm_once(self) -> None:
        loader = ModelLoader.instance()
        with mock.patch(
            "src.repo.model_loader._load_llm_backbone",
            return_value=_mock_handle(),
        ) as fresh:
            handles: list = []
            errors: list = []

            def worker() -> None:
                try:
                    handles.append(loader.load_llm_backbone())
                except Exception as exc:  # pragma: no cover -- we assert no error
                    errors.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [], f"workers raised: {errors}")
            # All threads received the same handle (identity, not equality).
            first = handles[0]
            for h in handles[1:]:
                self.assertIs(h, first)
            # The expensive load ran exactly once.
            self.assertEqual(fresh.call_count, 1)


if __name__ == "__main__":
    unittest.main()