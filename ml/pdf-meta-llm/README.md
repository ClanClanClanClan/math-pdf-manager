# PDF Metadata LLM Fine-Tuning Pipeline

Fine-tune Qwen2.5-7B-Instruct to extract title and author metadata from academic PDF text.

## Pipeline

```
PDFs (Author - Title.pdf)
    |
    v
extract_text.py  -->  raw_data.jsonl  (chat-format JSONL)
    |
    v
prepare_dataset.py  -->  datasets/{train,val,test}.jsonl  (filtered + split)
    |
    v
finetune.py (Colab A100)  -->  LoRA adapter + merged model
    |
    v
convert_to_gguf.sh  -->  ~/.mathpdf_models/gguf/qwen2.5-7b-pdfmeta-q4_k_m.gguf
```

## Scripts

| Script | Purpose |
|--------|---------|
| `extract_text.py` | Extract first 3 pages of PDF text + ground-truth labels from filenames |
| `prepare_dataset.py` | Quality filtering, deduplication, train/val/test splits |
| `inspect_dataset.py` | Data quality inspection and distribution analysis |
| `clean_jsonl.py` | Remove malformed JSON lines |
| `finetune.py` | LoRA fine-tune Qwen2.5-7B-Instruct (designed for Colab Pro A100) |
| `evaluate.py` | Evaluate extraction accuracy (exact match, fuzzy, token F1, author Jaccard) |
| `predict.py` | Run inference on a single PDF |
| `convert_to_gguf.sh` | Convert merged HuggingFace model to GGUF Q4_K_M |

## Quick Start

```bash
cd ml/pdf-meta-llm

# 1. Extract training data from PDF library
python scripts/extract_text.py ~/Dropbox/Work/Maths raw_data.jsonl --format chat

# 2. Filter and split into train/val/test
python scripts/prepare_dataset.py raw_data.jsonl --output-dir datasets/

# 3. Inspect data quality
python scripts/inspect_dataset.py datasets/

# 4. Fine-tune on Colab (upload datasets/ to Google Drive, open notebooks/train_qwen.ipynb)

# 5. Evaluate
python scripts/evaluate.py ~/Dropbox/Work/Maths --methods pipeline --sample 500
```

## Model Locations

- Fine-tuned GGUF: `~/.mathpdf_models/gguf/qwen2.5-7b-pdfmeta-q4_k_m.gguf`
- Base GGUF (fallback): `~/.mathpdf_models/gguf/qwen2.5-7b-instruct-q4_k_m.gguf`
- Runtime integration: `src/pdf_processing/llm_extractor.py` auto-detects the fine-tuned model
