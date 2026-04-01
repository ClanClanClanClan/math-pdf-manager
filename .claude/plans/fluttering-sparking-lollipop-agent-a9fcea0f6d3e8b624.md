# Research: Local LLM-Based Metadata Extraction from Academic PDFs

## 1. Best Small Models (3-8B) for Structured JSON Extraction on Apple Silicon

### Top Tier Recommendations

**Qwen2.5-7B-Instruct** -- STRONGEST RECOMMENDATION
- 7B params, Apache 2.0 license
- Specifically enhanced for structured data handling and JSON output vs prior versions
- Dominates structured data benchmarks among open models in its class
- Excellent GGUF availability from official and community quantizers
- HF: https://hf.co/Qwen/Qwen2.5-7B-Instruct
- GGUF: https://hf.co/Qwen/Qwen2.5-7B-Instruct-GGUF (official), https://hf.co/bartowski/Qwen2.5-7B-Instruct-GGUF (bartowski, imatrix quants)
- The MeXtract paper (see Section 3) chose Qwen 2.5 as the base for their metadata extraction models, validating this choice

**Qwen2.5-3B-Instruct** -- BEST LIGHTWEIGHT OPTION
- 3B params, much faster inference
- Still strong JSON capability inherited from the Qwen2.5 family
- Good for iteration/prototyping, may be sufficient for the task
- GGUF: https://hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF (official, 280K+ downloads)

**Phi-4-mini-instruct** -- STRONG ALTERNATIVE
- 3.8B params, MIT license
- Reasoning and multilingual performance comparable to 7B-9B models
- Native 128K context window (useful for full-paper processing)
- Strong at math/logic which may help with structured extraction
- GGUF: https://hf.co/unsloth/Phi-4-mini-instruct-GGUF (18K downloads), https://hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF

**Hermes-2-Pro-Llama-3-8B** -- BEST FOR FUNCTION CALLING / JSON
- 8B params, purpose-trained for function calling and JSON structured output
- 90% on function calling eval, 84% on JSON mode eval
- Has dedicated tokens (<tool_call>, etc.) for structured parsing
- Specifically designed for the exact use case of producing structured JSON
- GGUF: https://hf.co/NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF

### Second Tier

**SmolLM3-3B** (HuggingFace)
- 3B params, outperforms Llama-3.2-3B and Qwen2.5-3B on general benchmarks
- Newer model (July 2025), Apache 2.0
- GGUF: https://hf.co/unsloth/SmolLM3-3B-128K-GGUF

**Llama-3.2-3B-Instruct** (Meta)
- 3B params, well-tested, large community
- GGUF: https://hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF (355K downloads -- most popular)

**Mistral-7B-Instruct-v0.3**
- 7B params, Apache 2.0, very mature ecosystem
- Reliable workhorse but not specifically optimized for structured output
- GGUF: https://hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF

### Recommendation for This Project

Start with **Qwen2.5-7B-Instruct** (Q4_K_M quantization, ~4.5GB) as the primary model. If speed is critical, fall back to **Qwen2.5-3B-Instruct** (Q8_0, ~3.5GB). Use **Hermes-2-Pro-Llama-3-8B** as the backup if Qwen2.5 struggles with JSON adherence (unlikely given grammar constraints).

---

## 2. llama-cpp-python for Structured Output / Grammar-Constrained Generation

### JSON Schema Enforcement

**Yes, llama-cpp-python fully supports JSON schema enforcement** via two mechanisms:

1. **GBNF Grammar Constraints**: llama.cpp uses GBNF (GGML BNF) format grammars that guide token sampling at inference time. A built-in script `json-schema-to-grammar.py` converts JSON schemas to GBNF grammars. This eliminates invalid JSON entirely -- the model physically cannot produce tokens that violate the grammar.

2. **`response_format` API**: The OpenAI-compatible API in llama-cpp-python supports `response_format={"type": "json_object"}` and schema-constrained modes directly, using a combination of constrained sampling and speculative decoding.

3. **Instructor Library Integration**: The `instructor` library (3M+ monthly downloads) wraps llama-cpp-python with Pydantic model validation. You define a Pydantic BaseModel, patch the completion method with `mode=instructor.Mode.JSON_SCHEMA`, and get validated, typed output. Automatic retries on validation failure.
   - Docs: https://python.useinstructor.com/integrations/llama-cpp-python/

### Performance on Apple Silicon (Metal)

**Throughput Benchmarks** (from comparative study, arxiv:2511.05502):
- MLX: ~230 tok/s (fastest on Apple Silicon)
- MLC-LLM: ~190 tok/s
- llama.cpp: ~150 tok/s (short context)
- Ollama (wraps llama.cpp): 20-40 tok/s
- PyTorch MPS: ~7-9 tok/s

**Key observations:**
- llama.cpp uses Metal (GPU) backend on macOS, NOT MPS (which is PyTorch-specific)
- Metal acceleration is well-optimized and continuously improving
- For a 7B Q4_K_M model on M-series, expect 30-60 tok/s depending on context length and chip generation
- MLX is faster but llama.cpp has better structured output tooling

**Grammar Sampling Overhead:**
- Grammar constraints add measurable overhead, especially for complex schemas
- Simple JSON schemas (flat objects with string/int fields) have minimal impact (~5-10% slowdown)
- Deeply nested schemas with many optional fields can cause significant slowdown
- Newer frameworks like XGrammar and llguidance achieve near-zero overhead but are less mature for local use
- llguidance has been merged into llama.cpp (b4613+), offering ~50 microseconds of CPU time per token

### Practical Architecture for This Project

Use llama-cpp-python with the `instructor` library:
```
pip install llama-cpp-python instructor
```
- Define Pydantic models for metadata (title, authors, year, journal, DOI, etc.)
- Use JSON_SCHEMA mode for guaranteed valid output
- Metal GPU acceleration is automatic on macOS
- No network dependency -- fully in-process

**Alternative: Ollama + instructor** -- simpler setup, but 3-7x slower than raw llama.cpp.

---

## 3. Purpose-Built Models for Academic Paper Metadata Extraction

### MeXtract -- DIRECTLY RELEVANT (October 2025)

**This is the most relevant finding from this research.** MeXtract is a family of lightweight language models specifically designed for metadata extraction from scientific papers.

- **Models**: Fine-tuned from Qwen 2.5 at three scales:
  - [MeXtract-0.5B](https://hf.co/IVUL-KAUST/MeXtract-0.5B) (130 downloads)
  - [MeXtract-1.5B](https://hf.co/IVUL-KAUST/MeXtract-1.5B)
  - [MeXtract-3B](https://hf.co/IVUL-KAUST/MeXtract-3B)
- **Training**: LoRA fine-tuning on ~1,889 annotated examples, then DPO (preference optimization)
- **Performance**: State-of-the-art on the MOLE benchmark for metadata extraction
- **Training data available**:
  - SFT data: https://hf.co/datasets/IVUL-KAUST/mextract_sft
  - DPO data: https://hf.co/datasets/IVUL-KAUST/mextract_dpo
  - Papers corpus: https://hf.co/datasets/IVUL-KAUST/mextract_papers
- **Paper**: https://arxiv.org/abs/2510.06889
- **Code**: https://github.com/IVUL-KAUST/MOLE

**Caveat**: These models are in safetensors format, NOT GGUF. To use with llama.cpp, you would need to convert them. However, since they are Qwen2.5-based, conversion should be straightforward.

**Caveat 2**: MeXtract focuses on dataset-related metadata (dataset name, language, task, etc.) from NLP papers. Your use case (title, authors, year, journal) is simpler but different. The approach and training methodology are still highly informative.

### GROBID -- Production-Grade Traditional ML

- GitHub: https://github.com/kermitt2/grobid
- **Architecture**: Cascade of sequence labeling models (CRF + optional deep learning via DeLFT)
- **Capabilities**: Extracts 68 label types -- title, authors (first/middle/last), affiliations, journal, volume, issue, pages, DOI, PMID, abstract, sections, references, etc.
- **Performance**: 2-5 seconds per page, >90% accuracy, production-deployed at Semantic Scholar, ResearchGate, Internet Archive, HAL, Academia.edu, CERN
- **Deep Learning models**: Uses SciBERT-CRF, BidLSTM-CRF with GloVe/ELMo
- **Standalone?**: NO -- requires Java (JVM). DeLFT models are integrated via JEP (Java Embedded Python). Cannot extract just the ML models to use standalone in Python.
- **Docker available**: `docker pull lfoppiano/grobid:0.8.1` -- easiest deployment
- **REST API**: Can call from Python via requests library

**Recommendation**: GROBID is the gold standard for this task. Consider using it as a Docker service alongside LLM-based extraction for comparison/fallback. Its accuracy for basic metadata (title, authors, year) is very high.

### Nougat (Meta/Facebook Research)

- Paper: https://arxiv.org/abs/2308.13418
- HuggingFace: https://huggingface.co/docs/transformers/en/model_doc/nougat
- **Architecture**: Swin Transformer (vision) encoder + text decoder
- **Purpose**: Full OCR of academic PDFs to structured markup (Markdown/LaTeX)
- **No OCR pipeline needed** -- reads directly from page images
- **Use case**: Better suited for full-text extraction than just metadata
- **Limitation**: Heavier model, slower than text-based extraction from already-parsed PDF text

### SciBERT (Allen AI)

- HuggingFace: https://hf.co/allenai/scibert_scivocab_uncased
- BERT model pre-trained on 1.14M scientific papers (3.1B tokens)
- Used for NER, classification, and token classification on scientific text
- Could be fine-tuned for header/metadata token classification but would require significant custom work
- Better as an embedding model for scientific text similarity

### BiblioPage (March 2025)

- Paper: https://arxiv.org/abs/2503.19658
- Dataset of ~2,000 scanned title pages with 16 annotated bibliographic attributes
- Evaluated YOLO, DETR (object detection) + OCR, and VLLMs (Llama 3.2-Vision, GPT-4o)
- Best F1: 67 (Llama 3.2-Vision)
- More relevant for scanned/image-based PDFs

---

## 4. Fine-Tuning Approach for 500-2000 Training Examples

### Recommended Approach: QLoRA Fine-Tuning via MLX

**Why LoRA/QLoRA over alternatives:**

| Approach | Data Needed | Pros | Cons |
|----------|------------|------|------|
| Few-shot prompting | 0 (5-10 examples in prompt) | No training, instant iteration | Inconsistent, uses context window, slower inference |
| LoRA fine-tuning | 200-500 minimum | Near full-fine-tune quality, tiny adapter files (~10-50MB), fast training | Needs training pipeline setup |
| QLoRA | 200-500 minimum | Same as LoRA but ~60% less memory (7GB for 7B model) | Slightly lower quality than full LoRA |
| Full fine-tuning | 1000+ preferred | Best quality ceiling | Requires 28GB+ for 7B, impractical on most Macs |

**With 500-2000 examples, LoRA/QLoRA is the clear winner.** Research shows:
- 200-500 LoRA examples achieve 94% accuracy for structured extraction (invoice classification case study)
- Below 50-100 examples, you're doing "few-shot with extra steps" -- not enough signal
- Your range (500-2000) is ideal for LoRA

### Training on Apple Silicon with MLX

**Tool: `mlx-lm`** (Apple's MLX framework for LLMs)
- Native Apple Silicon optimization, uses unified memory efficiently
- QLoRA: ~7GB for a 7B model (fits on 16GB Mac)
- Supports Qwen2.5, Llama, Mistral, Phi models natively
- LoRA training at reasonable speed on M-series

**Training data format** (JSONL with chat template):
```jsonl
{"messages": [{"role": "system", "content": "Extract metadata from the following academic paper text. Return a JSON object with: title, authors (list), year, journal, volume, issue, pages, doi."}, {"role": "user", "content": "<first page text of PDF>"}, {"role": "assistant", "content": "{\"title\": \"...\", \"authors\": [...], ...}"}]}
```

Files needed: `train.jsonl`, `valid.jsonl` (optional), `test.jsonl` (optional)

**Creating training data from your library:**
Since you have correctly-named PDFs, the workflow would be:
1. Parse the first 1-2 pages of each PDF with a text extractor (PyMuPDF/pdfplumber)
2. Extract the ground-truth metadata from the filenames (and optionally CrossRef/OpenAlex API)
3. Format as JSONL chat pairs (input = page text, output = JSON metadata)
4. Split 80/10/10 train/valid/test

**MLX Training command:**
```bash
mlx_lm.lora \
  --model Qwen/Qwen2.5-3B-Instruct \
  --data ./training_data \
  --train \
  --iters 1000 \
  --batch-size 1 \
  --lora-layers 16
```

### Alternative: Unsloth for LoRA

- Unsloth (https://github.com/unslothai/unsloth) offers 2x faster LoRA training
- Works with Qwen2.5 models
- However, requires CUDA for full speed; Apple Silicon support is limited
- Better if you have access to a GPU machine or cloud instance for training

### Staged Approach Recommendation

1. **Phase 1**: Start with few-shot prompting (5-10 examples in the system prompt) using Qwen2.5-7B + grammar constraints. This requires zero training and will establish a baseline.
2. **Phase 2**: If accuracy is insufficient (<90%), create training data and LoRA fine-tune Qwen2.5-3B using MLX on your Mac.
3. **Phase 3**: If needed, scale to Qwen2.5-7B fine-tuning or increase training data.

---

## 5. GGUF Quantized Models Available on HuggingFace

### Primary Recommendations (sorted by suitability for this task)

| Model | Quantizer | Size (Q4_K_M) | Downloads | Link |
|-------|-----------|---------------|-----------|------|
| Qwen2.5-7B-Instruct-GGUF | Official (Qwen) | ~4.7GB | 47.7K | https://hf.co/Qwen/Qwen2.5-7B-Instruct-GGUF |
| Qwen2.5-7B-Instruct-GGUF | bartowski | ~4.7GB | varies | https://hf.co/bartowski/Qwen2.5-7B-Instruct-GGUF |
| Qwen2.5-3B-Instruct-GGUF | Official (Qwen) | ~2.1GB | 280.6K | https://hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF |
| Qwen2.5-3B-Instruct-GGUF | bartowski | ~2.1GB | 15.2K | https://hf.co/bartowski/Qwen2.5-3B-Instruct-GGUF |
| Hermes-2-Pro-Llama-3-8B-GGUF | NousResearch | ~4.7GB | varies | https://hf.co/NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF |
| Phi-4-mini-instruct-GGUF | unsloth | ~2.5GB | 18.3K | https://hf.co/unsloth/Phi-4-mini-instruct-GGUF |
| Phi-4-mini-instruct-GGUF | bartowski | ~2.5GB | 7.4K | https://hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF |
| Phi-3-mini-4k-instruct-gguf | Official (Microsoft) | ~2.4GB | 48.6K | https://hf.co/microsoft/Phi-3-mini-4k-instruct-gguf |
| Llama-3.2-3B-Instruct-GGUF | bartowski | ~2.0GB | 355.1K | https://hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF |
| Mistral-7B-Instruct-v0.3-GGUF | bartowski | ~4.4GB | 39.4K | https://hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF |
| SmolLM3-3B-128K-GGUF | unsloth | ~2.0GB | 3.1K | https://hf.co/unsloth/SmolLM3-3B-128K-GGUF |

### Quantization Level Guidance

- **Q8_0**: Best quality, ~8GB for 7B model. Use if you have 32GB+ RAM.
- **Q4_K_M**: Best quality/size tradeoff. Recommended default. ~4.5GB for 7B.
- **Q4_K_S**: Slightly smaller, marginally lower quality than Q4_K_M.
- **IQ4_XS**: Newer "importance matrix" quant, better quality than Q4 at same size, but slower on Apple Metal.

### Quantizer Notes

- **bartowski**: High-quality community quantizer, uses imatrix for better quality. Recommended.
- **unsloth**: Good quality, often first to release new models.
- **Official repos** (Qwen, Microsoft): Safe default choice.
- **TheBloke**: Pioneered GGUF quantization, but less active on newer models.

---

## Summary & Recommended Architecture

### Quickest Path to Production

1. **Use GROBID via Docker** for baseline metadata extraction (title, authors, year, journal, DOI). It handles >90% of cases reliably with zero ML work.
2. **Use Qwen2.5-7B-Instruct GGUF (Q4_K_M)** via llama-cpp-python + instructor for LLM-based extraction as a complementary/fallback approach.
3. **Grammar-constrain** the LLM output with a Pydantic schema to guarantee valid JSON.
4. **Compare results** from both approaches; use the LLM to fill gaps GROBID misses.

### If Building a Pure LLM Solution

1. Start with **Qwen2.5-7B-Instruct** + few-shot prompting + JSON grammar constraints
2. Evaluate on ~100 test PDFs
3. If accuracy < 90%, create training data from your correctly-named library
4. **LoRA fine-tune** Qwen2.5-3B-Instruct using MLX on your Mac
5. Convert fine-tuned model to GGUF for deployment via llama.cpp
6. Consider the MeXtract training approach (SFT + DPO) as a reference implementation

### Key Libraries

- `llama-cpp-python`: Core inference engine (Metal GPU acceleration)
- `instructor`: Pydantic-based structured output with validation + retries
- `mlx-lm`: LoRA/QLoRA fine-tuning on Apple Silicon
- `PyMuPDF` / `pdfplumber`: PDF text extraction (input to the LLM)
