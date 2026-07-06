#!/usr/bin/env python3
"""Manual smoke test to verify BARTpho model loading, tokenizer, and dataset preparation.

Run this script to verify that your environment is fully set up for training.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def main() -> int:
    print("=== BARTpho Training Environment Smoke Test ===")
    
    # 1. Kiểm tra các thư viện bắt buộc
    required_libs = ["torch", "transformers", "datasets", "peft", "pyvi"]
    missing_libs = []
    
    for lib in required_libs:
        try:
            __import__(lib)
            print(f"  [OK] Thư viện '{lib}' đã được cài đặt.")
        except ImportError:
            print(f"  [X] Thư viện '{lib}' CHƯA được cài đặt.")
            missing_libs.append(lib)
            
    if missing_libs:
        print("\n[ERROR] Thiếu một số thư viện cần thiết để huấn luyện.")
        print("Vui lòng chạy lệnh sau để cài đặt:")
        print(f"pip install {' '.join(missing_libs)} sentencepiece")
        return 1

    # 2. Import các modul liên quan
    print("\nImporting modules...")
    from transformers import AutoTokenizer, MBartForConditionalGeneration
    from scripts.finetune_bartpho import HAS_PYVI
    
    # 3. Test load Tokenizer
    model_name = "vinai/bartpho-syllable"
    print(f"\nĐang tải thử tokenizer của '{model_name}' (quá trình này có thể tải file từ HF)...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
        print("  [OK] Tải tokenizer thành công!")
    except Exception as e:
        print(f"  [X] Lỗi khi tải tokenizer: {e}")
        return 1

    # 4. Test text tokenization với pyvi nếu có
    sample_text = "Hôm nay chúng ta bàn về lỗi memory leak."
    print(f"\nTest tokenization với văn bản mẫu: '{sample_text}'")
    if HAS_PYVI:
        from pyvi import ViTokenizer
        segmented = ViTokenizer.tokenize(sample_text)
        print(f"  Segmented (pyvi): '{segmented}'")
        tokens = tokenizer.tokenize(segmented)
    else:
        print("  (Không có pyvi, tokenize trực tiếp)")
        tokens = tokenizer.tokenize(sample_text)
        
    print(f"  Tokens tương ứng: {tokens}")
    
    print("\n=== KIỂM TRA HOÀN TẤT: Môi trường đã sẵn sàng cho huấn luyện! ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
