"""Unit tests for ModelLoader singleton + cache + offline mock."""

import os
import unittest
from unittest import mock

from src.repo.model_loader import (
    LLM_BACKBONE_ID,
    MockLLMBackbone,
    ModelKind,
    ModelLoader,
)
from src.repo.prompts_vi import LLMTask
from src.repo.coherence_net import NSP_CKPT_PATH


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

    def test_nsp_ckpt_path_is_the_project_artifact(self) -> None:
        # Spec D1: cpt_4000.pth is the project's pre-trained artifact.
        self.assertTrue(NSP_CKPT_PATH.endswith("cpt_4000.pth"))

    def test_llm_backbone_id_is_vistral(self) -> None:
        self.assertEqual(LLM_BACKBONE_ID, "Viet-Mistral/Vistral-7B-Chat")

    def test_model_kind_enum_has_nsp_and_llm(self) -> None:
        self.assertEqual({k.name for k in ModelKind}, {"NSP", "LLM_BACKBONE"})


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
        self.assertEqual(mock_llm.call_count, 4)


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


class TestCaching(unittest.TestCase):
    def setUp(self) -> None:
        ModelLoader.reset_instance()

    def tearDown(self) -> None:
        ModelLoader.reset_instance()

    def test_nsp_handle_cached_on_second_access(self) -> None:
        loader = ModelLoader.instance()
        # Patch load_coherence_net's underlying loader to count invocations.
        with mock.patch("src.repo.model_loader._load_nsp_weights") as fresh:
            fresh.return_value = object()  # any object stand-in for the net
            a = loader.load_coherence_net()
            b = loader.load_coherence_net()
        self.assertIs(a, b)
        # Only one underlying load call.
        self.assertEqual(fresh.call_count, 1)

    def test_nsp_cache_hit_logs_debug_only(self) -> None:
        loader = ModelLoader.instance()
        with mock.patch("src.repo.model_loader._load_nsp_weights") as fresh:
            fresh.return_value = object()
            with mock.patch("transformers.AutoTokenizer.from_pretrained"):
                loader.load_coherence_net()
                with self.assertLogs("src.repo.model_loader", level="DEBUG") as logs:
                    loader.load_coherence_net()
        self.assertIn("model cache hit kind=nsp", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()


class TestModelLoaderConcurrency(unittest.TestCase):
    """C3: concurrent first-call must not load the model twice."""

    def setUp(self) -> None:
        ModelLoader.reset_instance()

    def tearDown(self) -> None:
        ModelLoader.reset_instance()

    def test_concurrent_first_call_loads_nsp_once(self) -> None:
        loader = ModelLoader.instance()
        with mock.patch("src.repo.model_loader._load_nsp_weights") as fresh:
            fresh.return_value = object()
            import threading

            handles: list = []
            errors: list = []

            def worker() -> None:
                try:
                    handles.append(loader.load_coherence_net())
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
