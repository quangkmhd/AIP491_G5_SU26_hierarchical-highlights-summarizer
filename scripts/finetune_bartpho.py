#!/usr/bin/env python3
"""
Script finetune model vinai/bartpho-syllable cho bài toán đặt tiêu đề (chapter title)
và tóm tắt (rolling summary) phân cấp cuộc họp.

Hỗ trợ cả Full Finetuning và Parameter-Efficient Fine-Tuning (LoRA) để tiết kiệm VRAM.
"""

import argparse
import logging
import os
import sys
import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    MBartForConditionalGeneration,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)

# Thử import pyvi để hỗ trợ tiếng Việt syllable-level tokenization
try:
    from pyvi import ViTokenizer
    HAS_PYVI = True
except ImportError:
    HAS_PYVI = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Finetune BARTpho-syllable for Meeting Recap")
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        default="vinai/bartpho-syllable",
        help="HF model path hoặc local path đến model gốc",
    )
    parser.add_argument(
        "--train_data_path",
        type=str,
        required=True,
        help="Đường dẫn đến file JSON chứa dữ liệu train (định dạng danh sách các dict với instruction, input, output)",
    )
    parser.add_argument(
        "--val_data_path",
        type=str,
        default=None,
        help="Đường dẫn đến file JSON chứa dữ liệu validation",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./bartpho_finetuned",
        help="Thư mục lưu checkpoint và model sau khi train",
    )
    parser.add_argument(
        "--use_lora",
        action="store_true",
        help="Sử dụng PEFT/LoRA để giảm bộ nhớ GPU (VRAM)",
    )
    parser.add_argument(
        "--lora_r", type=int, default=8, help="Rank r cho LoRA"
    )
    parser.add_argument(
        "--lora_alpha", type=int, default=16, help="Alpha cho LoRA"
    )
    parser.add_argument(
        "--lora_dropout", type=float, default=0.1, help="Dropout cho LoRA"
    )
    parser.add_argument(
        "--epochs", type=int, default=3, help="Số lượng epoch huấn luyện"
    )
    parser.add_argument(
        "--batch_size", type=int, default=4, help="Batch size trên mỗi GPU"
    )
    parser.add_argument(
        "--learning_rate", type=float, default=5e-5, help="Learning rate"
    )
    parser.add_argument(
        "--max_input_length",
        type=int,
        default=1024,
        help="Độ dài tối đa của chuỗi đầu vào (tokens)",
    )
    parser.add_argument(
        "--max_target_length",
        type=int,
        default=256,
        help="Độ dài tối đa của chuỗi đầu ra (tokens)",
    )
    parser.add_argument(
        "--segment_vietnamese",
        action="store_true",
        help="Sử dụng pyvi để phân tách từ/âm tiết trước khi tokenize (khuyến nghị cho bartpho-syllable)",
    )
    return parser.parse_args()


def load_custom_dataset(data_path, segment_vietnamese=False):
    """Load dữ liệu từ file JSON và chuyển đổi thành HuggingFace Dataset."""
    if not os.path.exists(data_path):
        logger.error(f"Không tìm thấy file dữ liệu tại: {data_path}")
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    processed_data = {
        "source": [],
        "target": []
    }

    for item in data:
        instruction = item.get("instruction", "")
        input_text = item.get("input", "")
        output_text = item.get("output", "")

        # BARTpho yêu cầu input ở dạng text thông thường
        # Ta có thể kết hợp instruction và input bằng dấu xuống dòng hoặc ký tự phân tách
        source_text = f"{instruction}\n{input_text}"
        target_text = output_text

        if segment_vietnamese and HAS_PYVI:
            source_text = ViTokenizer.tokenize(source_text)
            target_text = ViTokenizer.tokenize(target_text)

        processed_data["source"].append(source_text)
        processed_data["target"].append(target_text)

    return Dataset.from_dict(processed_data)


def main():
    args = parse_args()

    if args.segment_vietnamese and not HAS_PYVI:
        logger.warning(
            "Bạn chọn `--segment_vietnamese` nhưng thư viện `pyvi` chưa được cài đặt. "
            "Model sẽ tokenize trực tiếp mà không qua pyvi."
        )

    # 1. Load Tokenizer
    logger.info(f"Đang tải tokenizer từ: {args.model_name_or_path}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, use_fast=False)

    # 2. Load Dataset
    logger.info(f"Đang tải dữ liệu train từ: {args.train_data_path}")
    train_dataset = load_custom_dataset(args.train_data_path, args.segment_vietnamese)

    val_dataset = None
    if args.val_data_path:
        logger.info(f"Đang tải dữ liệu validation từ: {args.val_data_path}")
        val_dataset = load_custom_dataset(args.val_data_path, args.segment_vietnamese)

    # 3. Hàm tiền xử lý (Preprocessing function)
    def preprocess_function(examples):
        # Tokenize inputs
        model_inputs = tokenizer(
            examples["source"],
            max_length=args.max_input_length,
            truncation=True,
            padding=False,  # Sẽ được pad động bởi data collator
        )

        # Tokenize targets
        # labels đại diện cho đầu ra mong muốn
        labels = tokenizer(
            text_target=examples["target"],
            max_length=args.max_target_length,
            truncation=True,
            padding=False,
        )

        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    logger.info("Đang tiền xử lý dữ liệu...")
    tokenized_train = train_dataset.map(
        preprocess_function,
        batched=True,
        remove_columns=train_dataset.column_names,
        desc="Tokenizing train dataset",
    )

    tokenized_val = None
    if val_dataset:
        tokenized_val = val_dataset.map(
            preprocess_function,
            batched=True,
            remove_columns=val_dataset.column_names,
            desc="Tokenizing validation dataset",
        )

    # 4. Load Model
    logger.info(f"Đang tải model từ: {args.model_name_or_path}")
    device_map = "auto" if torch.cuda.is_available() else None
    
    # Sử dụng bfloat16 hoặc float16 tùy thuộc vào phần cứng hỗ trợ
    torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float32
    
    model = MBartForConditionalGeneration.from_pretrained(
        args.model_name_or_path,
        torch_dtype=torch_dtype,
        device_map=device_map,
    )

    # Đảm bảo decoder_start_token_id được set để tránh lỗi None khi train/eval
    if model.config.decoder_start_token_id is None:
        logger.info("Cấu hình decoder_start_token_id bị khuyết. Đang tự động gán bằng bos_token_id...")
        model.config.decoder_start_token_id = tokenizer.bos_token_id or tokenizer.eos_token_id
        
    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.pad_token_id


    # 5. Cấu hình LoRA nếu được yêu cầu
    if args.use_lora:
        logger.info("Đang cấu hình LoRA (PEFT)...")
        try:
            from peft import LoraConfig, get_peft_model, TaskType
        except ImportError:
            logger.error("Thư viện `peft` chưa được cài đặt. Vui lòng chạy `pip install peft` để dùng LoRA.")
            sys.exit(1)

        # Định cấu hình target modules phù hợp cho kiến trúc BART
        # Đối với BART, các module chính trong attention và linear layers là:
        # q_proj, k_proj, v_proj, out_proj trong self-attention và cross-attention
        peft_config = LoraConfig(
            task_type=TaskType.SEQ_2_SEQ_LM,
            inference_mode=False,
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
        )
        model = get_peft_model(model, peft_config)
        model.print_trainable_parameters()

    # 6. Định cấu hình Training Arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        evaluation_strategy="steps" if val_dataset else "no",
        eval_steps=500 if val_dataset else None,
        save_strategy="steps",
        save_steps=1000,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        weight_decay=0.01,
        save_total_limit=3,
        num_train_epochs=args.epochs,
        predict_with_generate=True,
        fp16=(torch_dtype == torch.float16 or torch.cuda.is_available()),
        logging_dir=os.path.join(args.output_dir, "logs"),
        logging_steps=100,
        report_to="tensorboard",
        dataloader_num_workers=2 if os.name != "nt" else 0,
        remove_unused_columns=False,
    )

    # 7. Khởi tạo Data Collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer,
        model=model,
        label_pad_token_id=-100,  # Bỏ qua loss của padding tokens
        pad_to_multiple_of=8 if torch.cuda.is_available() else None,
    )

    # 8. Khởi tạo Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_val,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    # 9. Bắt đầu huấn luyện
    logger.info("Bắt đầu huấn luyện...")
    trainer.train()

    # 10. Lưu model và tokenizer cuối cùng
    logger.info(f"Đang lưu model finetuned về thư mục: {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    logger.info("Hoàn tất huấn luyện và lưu model thành công!")


if __name__ == "__main__":
    main()
