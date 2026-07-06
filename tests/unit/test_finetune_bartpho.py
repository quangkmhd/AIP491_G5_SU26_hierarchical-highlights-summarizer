"""Unit tests for the BARTpho fine-tuning script.

Tests dataset loading, preprocessing, and Vietnamese segmentation logic.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    from scripts.finetune_bartpho import load_custom_dataset, HAS_PYVI
    HAS_TRAIN_DEPS = True
except ImportError:
    HAS_TRAIN_DEPS = False


@unittest.skipIf(not HAS_TRAIN_DEPS, "Thiếu thư viện huấn luyện (datasets, transformers)")
class FinetuneBartphoTests(unittest.TestCase):
    def setUp(self) -> None:
        # Tạo dữ liệu JSON tạm thời để test
        self.test_data = [
            {
                "instruction": "Tác vụ đặt tiêu đề:",
                "input": "Hôm nay họp bàn về lỗi memory leak.",
                "output": '{"title": "Lỗi Memory Leak"}'
            },
            {
                "instruction": "Tác vụ tóm tắt:",
                "input": "Tuấn sẽ sửa lỗi connection leak trước 5h.",
                "output": '{"summary": "Sửa lỗi connection"}'
            }
        ]
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False, encoding="utf-8")
        json.dump(self.test_data, self.temp_file)
        self.temp_file.close()

    def tearDown(self) -> None:
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_load_custom_dataset_returns_hf_dataset(self) -> None:
        dataset = load_custom_dataset(self.temp_file.name, segment_vietnamese=False)
        self.assertEqual(len(dataset), 2)
        self.assertIn("source", dataset.column_names)
        self.assertIn("target", dataset.column_names)
        
        # Kiểm tra nội dung gộp instruction và input
        self.assertEqual(dataset[0]["source"], "Tác vụ đặt tiêu đề:\nHôm nay họp bàn về lỗi memory leak.")
        self.assertEqual(dataset[0]["target"], '{"title": "Lỗi Memory Leak"}')

    def test_load_custom_dataset_with_segmentation(self) -> None:
        # Kiểm tra nếu pyvi được cài đặt
        if HAS_PYVI:
            dataset = load_custom_dataset(self.temp_file.name, segment_vietnamese=True)
            self.assertEqual(len(dataset), 2)
            # Từ "Hôm nay" trong tiếng Việt sẽ được pyvi segment thành "Hôm_nay"
            self.assertTrue("Hôm_nay" in dataset[0]["source"])
        else:
            # Nếu không có pyvi, hàm vẫn chạy bình thường và không phân tách bằng gạch dưới
            dataset = load_custom_dataset(self.temp_file.name, segment_vietnamese=True)
            self.assertEqual(len(dataset), 2)
            self.assertTrue("Hôm nay" in dataset[0]["source"])

    def test_missing_file_raises_system_exit(self) -> None:
        with self.assertRaises(SystemExit):
            load_custom_dataset("non_existent_file.json")


if __name__ == "__main__":
    unittest.main()
