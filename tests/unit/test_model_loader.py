"""Unit tests for the dual local seq2seq model loader."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from src.repo.model_loader import (
    TOPIC_TITLER_PATH,
    ModelHandle,
    ModelKind,
    ModelLoadError,
    ModelLoader,
)


def _handle(kind: ModelKind) -> ModelHandle:
    return ModelHandle(kind, object(), object(), "cuda", f"/models/{kind.value}")


class ModelLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        ModelLoader.reset_instance()

    def tearDown(self) -> None:
        ModelLoader.reset_instance()

    def test_singleton_can_be_reset(self) -> None:
        first = ModelLoader.instance()
        self.assertIs(first, ModelLoader.instance())
        ModelLoader.reset_instance()
        self.assertIsNot(first, ModelLoader.instance())

    def test_model_kinds_are_task_specific(self) -> None:
        self.assertEqual(
            {kind.name for kind in ModelKind},
            {"CHUNK_SUMMARIZER", "TOPIC_TITLER"},
        )

    def test_topic_titler_uses_selected_checkpoint(self) -> None:
        self.assertEqual(TOPIC_TITLER_PATH.name, "checkpoint-230")

    @mock.patch("src.repo.model_loader._load_seq2seq_handle")
    def test_handles_cache_independently(self, load: mock.Mock) -> None:
        load.side_effect = lambda kind, path: _handle(kind)
        loader = ModelLoader()
        self.assertIs(loader.load_chunk_summarizer(), loader.load_chunk_summarizer())
        self.assertIs(loader.load_topic_titler(), loader.load_topic_titler())
        self.assertEqual(load.call_count, 2)

    @mock.patch("src.repo.model_loader._load_seq2seq_handle")
    def test_concurrent_first_call_loads_once(self, load: mock.Mock) -> None:
        load.return_value = _handle(ModelKind.CHUNK_SUMMARIZER)
        loader = ModelLoader()
        handles: list[ModelHandle] = []
        threads = [threading.Thread(target=lambda: handles.append(loader.load_chunk_summarizer())) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(load.call_count, 1)
        self.assertTrue(all(handle is handles[0] for handle in handles))

    @mock.patch("torch.cuda.is_available", return_value=False)
    def test_cuda_is_required(self, _: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ModelLoadError, r"CUDA.*fix"):
                from src.repo.model_loader import _load_seq2seq_handle
                _load_seq2seq_handle(ModelKind.CHUNK_SUMMARIZER, Path(directory))

    @mock.patch("torch.cuda.is_available", return_value=True)
    def test_missing_files_are_actionable(self, _: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ModelLoadError, r"missing=.*fix"):
                from src.repo.model_loader import _load_seq2seq_handle
                _load_seq2seq_handle(ModelKind.TOPIC_TITLER, Path(directory))

    def test_legacy_extra_special_tokens_are_normalized_for_newer_transformers(self) -> None:
        from src.repo.model_loader import _tokenizer_compat_kwargs

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "tokenizer_config.json").write_text(
                json.dumps({"extra_special_tokens": ["<extra_id_0>", "<extra_id_1>"]}),
                encoding="utf-8",
            )

            self.assertEqual(_tokenizer_compat_kwargs(path), {"extra_special_tokens": {}})


if __name__ == "__main__":
    unittest.main()
