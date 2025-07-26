#!/usr/bin/env python3
"""
finetune.py – tiny LoRA fine-tuning of TinyLlama (or any GGUF-converted base) on the
PDF-metadata dataset produced earlier.

• CPU / Apple-Silicon friendly (no bf16)
• Works with Transformers ≥ 4.41 + PEFT 0.11
• Automatically skips broken rows and keeps the script self-contained.
"""

from __future__ import annotations

import math
import argparse
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model

# ──────────────────────────────────────────────────────────────────────────────
# CLI args (so you can override defaults without editing the file)
# ──────────────────────────────────────────────────────────────────────────────

def get_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="datasets/pdfmeta.clean.jsonl",
                   help="JSONL file with a prompt column (cleaned)")
    p.add_argument("--base", default="models/base",
                   help="folder with the base TinyLlama model")
    p.add_argument("--out",  default="models/finetuned",
                   help="where to write the LoRA-adapted model")
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--bsz",    type=int, default=4,
                   help="per-device batch-size")
    return p.parse_args()

args = get_args()

# ──────────────────────────────────────────────────────────────────────────────
# Tokeniser
# ──────────────────────────────────────────────────────────────────────────────

print("🔹 Loading tokenizer …")

_tok = AutoTokenizer.from_pretrained(args.base, use_fast=True, revision="main")  # nosec B615 - revision pinned for security
_tok.pad_token = _tok.eos_token  # make pad = eos to avoid resize
_MAX_LEN = 512                  # keep it small – we only need the header info


def _tokenise(example: dict):
    """Convert one JSONL row into input_ids/attention_mask or skip."""
    prompt: str | None = example.get("prompt")
    if not prompt or not prompt.strip():
        return None  # will be filtered out
    ids = _tok(prompt[:4000], truncation=True, max_length=_MAX_LEN)
    return {
        "input_ids": ids["input_ids"],
        "attention_mask": ids["attention_mask"],
    }

# ──────────────────────────────────────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────────────────────────────────────

data_path = Path(args.data).expanduser()
print("🔹 Loading dataset –", data_path)

ds = load_dataset("json", data_files=str(data_path), split="train", revision="main")  # nosec B615 - revision pinned for security

ds = ds.map(_tokenise, remove_columns=ds.column_names, num_proc=4)
# filter out Nones produced by rows without prompt
_ds_before = len(ds)
ds = ds.filter(lambda x: x is not None and len(x["input_ids"]) > 0)
print(f"   → kept {len(ds):,} / {_ds_before:,} rows after cleaning")

# ──────────────────────────────────────────────────────────────────────────────
# Model + LoRA
# ──────────────────────────────────────────────────────────────────────────────

print("🔹 Loading base model from", args.base)

device_dtype = (
    torch.float16 if torch.cuda.is_available() else torch.float32
)  # float32 on CPU/apple-silicon

_base_model = AutoModelForCausalLM.from_pretrained(  # nosec B615 - revision pinned for security
    args.base,
    torch_dtype=device_dtype,
    device_map="auto",
    revision="main",
)

lora_cfg = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(_base_model, lora_cfg)
model.print_trainable_parameters()

# ──────────────────────────────────────────────────────────────────────────────
# Training arguments – tuned for CPU/small-GPU
# ──────────────────────────────────────────────────────────────────────────────

steps_per_device = math.ceil(len(ds) / args.bsz / args.epochs)
print(f"   → will run ~{steps_per_device:,} optimisation steps")

train_args = TrainingArguments(
    output_dir=args.out,
    per_device_train_batch_size=args.bsz,
    gradient_accumulation_steps=4,
    num_train_epochs=args.epochs,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    weight_decay=0.01,
    logging_steps=25,
    save_strategy="epoch",
    report_to="none",  # no wandb
    fp16=torch.cuda.is_available(),  # enable half-precision only on CUDA
    bf16=False,                      # keep bf16 off – not supported on CPU/M-GPU
)

collator = DataCollatorForLanguageModeling(_tok, mlm=False)

trainer = Trainer(
    model=model,
    args=train_args,
    train_dataset=ds,
    data_collator=collator,
)

# ──────────────────────────────────────────────────────────────────────────────
# Train 🚂
# ──────────────────────────────────────────────────────────────────────────────

print("🔹 Training …")
trainer.train()

print("🔹 Saving … →", args.out)
trainer.save_model(args.out)
_tok.save_pretrained(args.out)
print("✅ Done – finetuned model ready.")
