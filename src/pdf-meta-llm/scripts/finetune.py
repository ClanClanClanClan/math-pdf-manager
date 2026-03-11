#!/usr/bin/env python3
"""
Fine-tune Qwen2.5-7B-Instruct on the PDF metadata extraction dataset.

Designed for **Google Colab Pro + A100** (40–80 GB VRAM).  Uses LoRA for
parameter-efficient fine-tuning with chat-template tokenisation and label
masking (loss only on assistant response tokens).

Input: Chat-format JSONL files produced by ``prepare_dataset.py``::

    datasets/train.jsonl
    datasets/val.jsonl

Each line is ``{"messages": [{"role": "system", ...}, {"role": "user", ...},
{"role": "assistant", ...}]}``.

Usage::

    # Standard training (Colab A100)
    python finetune.py --data-dir datasets/ --output-dir models/finetuned

    # Custom hyperparameters
    python finetune.py --data-dir datasets/ --output-dir models/finetuned \\
        --epochs 3 --lr 5e-5 --batch-size 4 --grad-accum 4

    # Resume from checkpoint
    python finetune.py --data-dir datasets/ --output-dir models/finetuned \\
        --resume-from models/finetuned/checkpoint-500

Output:
    - LoRA adapter weights at ``<output-dir>/``
    - Merged full model at ``<output-dir>/merged/``
    - Training metrics in ``<output-dir>/training_metrics.json``
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from datasets import Dataset, load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    TrainerCallback,
)
from peft import LoraConfig, get_peft_model, PeftModel

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
MAX_SEQ_LEN = 2048

# LoRA configuration — targets all linear projections in attention + MLP
LORA_CONFIG = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# Default training hyperparameters (A100-optimised)
DEFAULT_EPOCHS = 2
DEFAULT_LR = 1e-4
DEFAULT_BATCH_SIZE = 4
DEFAULT_GRAD_ACCUM = 4  # effective batch = 16
DEFAULT_WARMUP_RATIO = 0.05
DEFAULT_WEIGHT_DECAY = 0.01


# -----------------------------------------------------------------------
# Chat template tokenisation with label masking
# -----------------------------------------------------------------------

def tokenize_chat(
    example: Dict[str, Any],
    tokenizer: AutoTokenizer,
    max_length: int = MAX_SEQ_LEN,
) -> Dict[str, Any]:
    """Tokenise a chat-format example with label masking.

    The loss is computed only on assistant response tokens — system and user
    message tokens have their labels set to -100 (ignored by CrossEntropyLoss).
    """
    messages = example["messages"]

    # Tokenise the full conversation using the model's chat template
    full_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False
    )
    full_ids = tokenizer(
        full_text,
        truncation=True,
        max_length=max_length,
        return_attention_mask=True,
    )

    input_ids = full_ids["input_ids"]
    attention_mask = full_ids["attention_mask"]

    # Find where the assistant response starts to create label mask
    # Tokenise everything BEFORE the assistant response
    non_assistant_messages = messages[:-1]  # system + user
    prefix_text = tokenizer.apply_chat_template(
        non_assistant_messages, tokenize=False, add_generation_prompt=True
    )
    prefix_ids = tokenizer(
        prefix_text, truncation=True, max_length=max_length
    )["input_ids"]
    prefix_len = len(prefix_ids)

    # Labels: -100 for prefix (system + user), real token ids for assistant
    labels = [-100] * prefix_len + input_ids[prefix_len:]

    # Pad labels to match input_ids length (shouldn't differ, but safety)
    if len(labels) < len(input_ids):
        labels += [-100] * (len(input_ids) - len(labels))
    labels = labels[:len(input_ids)]

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


# -----------------------------------------------------------------------
# Data collator with padding
# -----------------------------------------------------------------------

class ChatDataCollator:
    """Pads input_ids, attention_mask, and labels to the longest sequence in batch."""

    def __init__(self, tokenizer: AutoTokenizer):
        self.pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        max_len = max(len(f["input_ids"]) for f in features)

        input_ids = []
        attention_mask = []
        labels = []

        for f in features:
            pad_len = max_len - len(f["input_ids"])
            input_ids.append(f["input_ids"] + [self.pad_token_id] * pad_len)
            attention_mask.append(f["attention_mask"] + [0] * pad_len)
            labels.append(f["labels"] + [-100] * pad_len)

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


# -----------------------------------------------------------------------
# Metrics callback
# -----------------------------------------------------------------------

class MetricsLogger(TrainerCallback):
    """Log training metrics to a JSON file."""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.metrics: List[Dict[str, Any]] = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            entry = {
                "step": state.global_step,
                "epoch": round(state.epoch, 3) if state.epoch else 0,
                **{k: v for k, v in logs.items() if isinstance(v, (int, float))},
            }
            self.metrics.append(entry)

    def on_train_end(self, args, state, control, **kwargs):
        with open(self.output_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        print(f"Training metrics saved to {self.output_path}")


# -----------------------------------------------------------------------
# Main training function
# -----------------------------------------------------------------------

def train(
    data_dir: Path,
    output_dir: Path,
    base_model: str = BASE_MODEL,
    epochs: int = DEFAULT_EPOCHS,
    lr: float = DEFAULT_LR,
    batch_size: int = DEFAULT_BATCH_SIZE,
    grad_accum: int = DEFAULT_GRAD_ACCUM,
    resume_from: Optional[str] = None,
    merge_after: bool = True,
) -> None:
    """Run LoRA fine-tuning."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load tokenizer
    # ------------------------------------------------------------------
    print(f"Loading tokenizer from {base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ------------------------------------------------------------------
    # 2. Load and tokenise datasets
    # ------------------------------------------------------------------
    train_path = data_dir / "train.jsonl"
    val_path = data_dir / "val.jsonl"

    if not train_path.exists():
        raise FileNotFoundError(f"Training data not found: {train_path}")

    print(f"Loading training data from {train_path}...")
    train_ds = load_dataset("json", data_files=str(train_path), split="train")

    val_ds = None
    if val_path.exists():
        print(f"Loading validation data from {val_path}...")
        val_ds = load_dataset("json", data_files=str(val_path), split="train")

    print(f"Tokenising {len(train_ds):,} training examples...")
    train_ds = train_ds.map(
        lambda x: tokenize_chat(x, tokenizer, MAX_SEQ_LEN),
        remove_columns=train_ds.column_names,
        num_proc=4,
        desc="Tokenising train",
    )
    # Filter out examples that are too short (< 50 tokens)
    before = len(train_ds)
    train_ds = train_ds.filter(lambda x: len(x["input_ids"]) >= 50)
    print(f"Kept {len(train_ds):,}/{before:,} training examples after filtering")

    if val_ds is not None:
        val_ds = val_ds.map(
            lambda x: tokenize_chat(x, tokenizer, MAX_SEQ_LEN),
            remove_columns=val_ds.column_names,
            num_proc=4,
            desc="Tokenising val",
        )
        val_ds = val_ds.filter(lambda x: len(x["input_ids"]) >= 50)
        print(f"Validation: {len(val_ds):,} examples")

    # ------------------------------------------------------------------
    # 3. Load model
    # ------------------------------------------------------------------
    print(f"Loading base model {base_model}...")
    compute_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=compute_dtype,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="flash_attention_2" if torch.cuda.is_available() else "eager",
    )
    model.config.use_cache = False  # Required for gradient checkpointing

    # ------------------------------------------------------------------
    # 4. Apply LoRA
    # ------------------------------------------------------------------
    print("Applying LoRA configuration...")
    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()

    # ------------------------------------------------------------------
    # 5. Training arguments
    # ------------------------------------------------------------------
    effective_batch = batch_size * grad_accum
    total_steps = math.ceil(len(train_ds) / effective_batch) * epochs
    print(f"Effective batch size: {effective_batch}")
    print(f"Total training steps: ~{total_steps:,}")

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_ratio=DEFAULT_WARMUP_RATIO,
        weight_decay=DEFAULT_WEIGHT_DECAY,
        logging_steps=10,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=3,
        eval_strategy="steps" if val_ds else "no",
        eval_steps=500 if val_ds else None,
        bf16=torch.cuda.is_available(),
        fp16=False,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to="none",
        dataloader_num_workers=2,
        remove_unused_columns=False,
    )

    # ------------------------------------------------------------------
    # 6. Train
    # ------------------------------------------------------------------
    collator = ChatDataCollator(tokenizer)
    metrics_logger = MetricsLogger(output_dir / "training_metrics.json")

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
        callbacks=[metrics_logger],
    )

    print("Starting training...")
    t0 = time.monotonic()

    if resume_from:
        trainer.train(resume_from_checkpoint=resume_from)
    else:
        trainer.train()

    elapsed = time.monotonic() - t0
    print(f"Training completed in {elapsed / 60:.1f} minutes")

    # Save LoRA adapter
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"LoRA adapter saved to {output_dir}")

    # ------------------------------------------------------------------
    # 7. Merge LoRA into base model
    # ------------------------------------------------------------------
    if merge_after:
        merge_dir = output_dir / "merged"
        print(f"Merging LoRA weights into base model -> {merge_dir}...")

        # Reload base model for merging
        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=compute_dtype,
            device_map="auto",
            trust_remote_code=True,
        )
        merged = PeftModel.from_pretrained(base, str(output_dir))
        merged = merged.merge_and_unload()

        merge_dir.mkdir(parents=True, exist_ok=True)
        merged.save_pretrained(str(merge_dir))
        tokenizer.save_pretrained(str(merge_dir))
        print(f"Merged model saved to {merge_dir}")

    print("Done!")


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune Qwen2.5-7B-Instruct on PDF metadata extraction",
    )
    parser.add_argument(
        "--data-dir", type=Path, required=True,
        help="Directory containing train.jsonl and val.jsonl",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("models/finetuned"),
        help="Output directory for LoRA adapter and merged model",
    )
    parser.add_argument(
        "--base-model", type=str, default=BASE_MODEL,
        help=f"HuggingFace model ID (default: {BASE_MODEL})",
    )
    parser.add_argument(
        "--epochs", type=int, default=DEFAULT_EPOCHS,
        help=f"Number of training epochs (default: {DEFAULT_EPOCHS})",
    )
    parser.add_argument(
        "--lr", type=float, default=DEFAULT_LR,
        help=f"Learning rate (default: {DEFAULT_LR})",
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"Per-device batch size (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--grad-accum", type=int, default=DEFAULT_GRAD_ACCUM,
        help=f"Gradient accumulation steps (default: {DEFAULT_GRAD_ACCUM})",
    )
    parser.add_argument(
        "--resume-from", type=str, default=None,
        help="Resume from checkpoint directory",
    )
    parser.add_argument(
        "--no-merge", action="store_true",
        help="Skip merging LoRA into base model after training",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        base_model=args.base_model,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        resume_from=args.resume_from,
        merge_after=not args.no_merge,
    )


if __name__ == "__main__":
    main()
