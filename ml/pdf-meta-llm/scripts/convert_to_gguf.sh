#!/usr/bin/env bash
#
# Convert a merged HuggingFace model to GGUF Q4_K_M format.
#
# Prerequisites:
#   - llama.cpp built locally (cmake -B build && cmake --build build)
#   - Python with: pip install gguf numpy sentencepiece
#
# Usage:
#   ./convert_to_gguf.sh <merged_model_dir> [output_name]
#
# Examples:
#   ./convert_to_gguf.sh models/finetuned/merged
#   ./convert_to_gguf.sh models/finetuned/merged qwen2.5-7b-pdfmeta-q4_k_m.gguf

set -euo pipefail

MERGED_DIR="${1:?Usage: $0 <merged_model_dir> [output_name]}"
OUTPUT_NAME="${2:-qwen2.5-7b-pdfmeta-q4_k_m.gguf}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/llama.cpp}"

# Validate inputs
if [ ! -d "$MERGED_DIR" ]; then
    echo "Error: Model directory not found: $MERGED_DIR"
    exit 1
fi

if [ ! -f "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" ]; then
    echo "Error: llama.cpp not found at $LLAMA_CPP_DIR"
    echo "Set LLAMA_CPP_DIR or clone: git clone https://github.com/ggerganov/llama.cpp"
    exit 1
fi

QUANTIZE_BIN="$LLAMA_CPP_DIR/build/bin/llama-quantize"
if [ ! -f "$QUANTIZE_BIN" ]; then
    echo "Error: llama-quantize not found. Build llama.cpp first:"
    echo "  cd $LLAMA_CPP_DIR && cmake -B build && cmake --build build --config Release"
    exit 1
fi

# Output directory
OUTPUT_DIR="$HOME/.mathpdf_models/gguf"
mkdir -p "$OUTPUT_DIR"

FP16_PATH="/tmp/model-fp16.gguf"
FINAL_PATH="$OUTPUT_DIR/$OUTPUT_NAME"

echo "=== GGUF Conversion Pipeline ==="
echo "Input:  $MERGED_DIR"
echo "Output: $FINAL_PATH"
echo ""

# Step 1: Convert to GGUF FP16
echo "[1/2] Converting HF model to GGUF FP16..."
python3 "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" \
    "$MERGED_DIR" \
    --outfile "$FP16_PATH" \
    --outtype f16

# Step 2: Quantize to Q4_K_M
echo "[2/2] Quantizing to Q4_K_M..."
"$QUANTIZE_BIN" "$FP16_PATH" "$FINAL_PATH" Q4_K_M

# Cleanup
rm -f "$FP16_PATH"

# Report
SIZE=$(du -h "$FINAL_PATH" | cut -f1)
echo ""
echo "=== Done ==="
echo "GGUF model: $FINAL_PATH ($SIZE)"
echo ""
echo "The LLMMetadataExtractor will automatically detect this model."
