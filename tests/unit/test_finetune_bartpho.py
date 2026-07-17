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
    from scripts.finetune_bartpho_custom import load_custom_dataset as load_custom_dataset_custom
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

    def test_load_custom_dataset_jsonl_and_split(self) -> None:
        # Create a mock JSONL file containing 10 meeting objects
        mock_meetings = []
        for i in range(10):
            mock_meetings.append({
                "dialogue": [
                    {"emotion": "no_emotion", "act": "directive", "text": f"turn {j}", "text_vi": f"câu {j}"}
                    for j in range(8)
                ],
                "title": f"Tiêu đề {i}",
                "summary": [f"Tóm tắt {i}"]
            })
            
        temp_jsonl = tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w+", delete=False, encoding="utf-8")
        for m in mock_meetings:
            temp_jsonl.write(json.dumps(m, ensure_ascii=False) + "\n")
        temp_jsonl.close()
        
        try:
            # 1. Test load entire file using bartpho custom
            dataset_full = load_custom_dataset_custom(temp_jsonl.name, segment_vietnamese=False)
            # 10 meetings * (1 title + 1 chunk summary) = 20 examples
            self.assertEqual(len(dataset_full), 20)
            
            # 2. Test 90/10 split on bartpho custom
            dataset_train = load_custom_dataset_custom(temp_jsonl.name, segment_vietnamese=False, split_type="train")
            dataset_val = load_custom_dataset_custom(temp_jsonl.name, segment_vietnamese=False, split_type="val")
            
            # 90% of 10 meetings = 9 meetings. 9 * 2 = 18 examples
            self.assertEqual(len(dataset_train), 18)
            # 10% of 10 meetings = 1 meeting. 1 * 2 = 2 examples
            self.assertEqual(len(dataset_val), 2)
            
            # 3. Test load and split on finetune_bartpho (standard)
            dataset_train_std = load_custom_dataset(temp_jsonl.name, segment_vietnamese=False, split_type="train")
            dataset_val_std = load_custom_dataset(temp_jsonl.name, segment_vietnamese=False, split_type="val")
            self.assertEqual(len(dataset_train_std), 18)
            self.assertEqual(len(dataset_val_std), 2)
            
        finally:
            if os.path.exists(temp_jsonl.name):
                os.remove(temp_jsonl.name)


if __name__ == "__main__":
    unittest.main()
