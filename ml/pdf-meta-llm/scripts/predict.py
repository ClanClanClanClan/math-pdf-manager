#!/usr/bin/env python3
"""
Predict title & author for a single PDF.

Usage
-----
    python -m scripts.predict /path/to/file.pdf
"""

from __future__ import annotations
from pathlib import Path
import json
import re
import sys
import textwrap
import warnings
import contextlib

# ── heavy deps
import torch
import peft
import transformers

# ── local helper (relative import *inside* `scripts`)
from .extract_text import extract                # first-pages extraction


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MODEL_BASE = Path(__file__).resolve().parent.parent / "models" / "base"
MODEL_LORA = Path(__file__).resolve().parent.parent / "models" / "finetuned"

MAX_CTX    = 2048                              # TinyLlama’s context window
N_PAGES    = 3                                 # pages to OCR / parse
GEN_ARGS   = dict(
    max_new_tokens = 64,
    do_sample      = False,                    # deterministic
)

DEVICE     = (
    "mps"
    if torch.backends.mps.is_available()
    else "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

# ─────────────────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────────────────

_tokenizer: transformers.PreTrainedTokenizer | None = None
_model:     torch.nn.Module | None = None


def _load_model():
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model

    print("🔹 loading model …", file=sys.stderr)
    tok = transformers.AutoTokenizer.from_pretrained(MODEL_BASE, revision="main")  # nosec B615 - revision pinned for security
    base = transformers.AutoModelForCausalLM.from_pretrained(  # nosec B615 - revision pinned for security
        MODEL_BASE, device_map=DEVICE, load_in_8bit=False, torch_dtype=torch.float16, revision="main"
    )
    model = peft.PeftModel.from_pretrained(base, MODEL_LORA)
    model.to(DEVICE).eval()
    _tokenizer, _model = tok, model
    return tok, model


# ─────────────────────────────────────────────────────────────────────────────
# Prompt template
# ─────────────────────────────────────────────────────────────────────────────

SYS_PROMPT = textwrap.dedent(
    """\
    You are a metadata-extraction assistant. Return **only** valid JSON with
    exactly two keys: "title" and "author". No other keys and no extra text.
    """
).strip()


def build_prompt(pages: str) -> str:
    return (
        f"<|system|>\n{SYS_PROMPT}\n<|user|>\n"
        f"Here are the first pages of a PDF:\n{pages}\n\nExtract the metadata."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Regex fallback for really bad model replies
# ─────────────────────────────────────────────────────────────────────────────

HTTP_PAT    = re.compile(r"https?://\S+")
BOILER_PAT  = re.compile(r"^(abstract|résumé|keywords|introduction)[: ]?", re.I)


def _looks_bad(title: str) -> bool:
    return (
        len(title) < 10
        or len(title) > 180
        or HTTP_PAT.search(title)
        or BOILER_PAT.match(title)
    )


def regex_fallback(pages_or_reply: str) -> dict[str, str] | None:
    """
    Heuristic extraction used when the LLM fails.
    Handles raw PDF pages OR the LLM’s non-JSON reply
    (e.g. “1. Title: … 2. Author: …” or bullet lists).
    """
    # --- Case 1: model wrote “Title:” / “Author:” lines -------------------
    m1 = re.search(r"title\s*[:\-]\s*(.+)", pages_or_reply, re.I)
    m2 = re.search(r"author[s]?\s*[:\-]\s*([^\n]+)", pages_or_reply, re.I)
    if m1 and m2:
        title  = m1.group(1).strip(" .")
        author = m2.group(1).strip(" .")
        if title and author and not _looks_bad(title):
            return {"title": title, "author": author}

    # --- Case 2: scan first PDF lines for plausible title -----------------
    lines = [ln.strip() for ln in pages_or_reply.splitlines() if ln.strip()]
    title = next(
        (
            ln for ln in lines
            if 10 < len(ln) < 150
            and re.search(r"[A-Za-z]", ln)
            and not _looks_bad(ln)
        ),
        None,
    )
    if not title:
        return None

    start = lines.index(title) + 1
    auth: list[str] = []
    for ln in lines[start : start + 6]:                  # up to 6 lines
        ln_clean = re.sub(r"^[\d\W_]+", "", ln).strip()  # strip bullets
        if re.match(r"^[A-Z][\w .\-']{3,120}$", ln_clean) and not ln_clean.endswith("."):
            auth.append(ln_clean)
        else:
            break

    if auth:
        return {"title": title.rstrip(" ."), "author": ", ".join(auth)}

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Generation wrapper
# ─────────────────────────────────────────────────────────────────────────────

def generate(pages: str) -> dict[str, str]:
    tok, model = _load_model()

    prompt = build_prompt(pages)
    inp    = tok(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_CTX - GEN_ARGS["max_new_tokens"],
    ).to(DEVICE)

    # Prevent mps/cuda mismatch if tokenizer auto-moved tensors to CPU
    with torch.inference_mode(), contextlib.suppress(torch.cuda.OutOfMemoryError):
        out_ids = model.generate(**inp, **GEN_ARGS)

    reply = tok.decode(out_ids[0][inp["input_ids"].shape[1] :], skip_special_tokens=True).strip()

    # ---------- try to rescue embedded JSON ------------------------------
    if "{" in reply and "}" in reply:
        try:
            start = reply.index("{")
            end   = reply.rindex("}") + 1
            return json.loads(reply[start:end])
        except Exception:
            pass

    # ---------- plain JSON failed → regex heuristics ---------------------
    with contextlib.suppress(Exception):
        return json.loads(reply)  # maybe it was actually JSON but with noise

    meta = regex_fallback(reply) or regex_fallback(pages)
    if meta:
        return meta

    raise ValueError(f"Model reply not JSON » {reply!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.predict /path/to/file.pdf", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1]).expanduser()
    if not pdf_path.is_file():
        print(f"File not found: {pdf_path}", file=sys.stderr)
        sys.exit(2)

    warnings.filterwarnings("ignore", category=UserWarning, module="pymupdf")

    print("📝  extracting first pages …", file=sys.stderr)
    pages = extract(pdf_path, n_pages=N_PAGES)

    print("📝  predicting …", file=sys.stderr)
    meta = generate(pages)

    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()