# Environment Setup Guide

This guide explains how to prepare a working environment for the Academic Paper Management System.

## 1. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** The CLI requires `PyYAML`, `aiohttp`, and `playwright`. Installing from `requirements.txt` ensures these libraries are available.

## 3. Install Playwright Browsers (for institutional automation)

```bash
playwright install firefox chromium webkit
```

## 4. Optional: Node Dependencies for the Frontend

```bash
cd frontend
npm install
cd ..
```

## 5. Verify the Installation

```bash
python -m pytest tests/unit/test_smoke_pipeline.py
python src/main.py --help
```

If `python src/main.py --help` raises a `RuntimeError` about `PyYAML`, reinstall dependencies using Step 2.

---

For automated setup, see `scripts/bootstrap_env.sh`.
