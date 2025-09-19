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

If you plan to use institutional access automation, set the following environment variables before running downloads:

```bash
export INSTITUTIONAL_USERNAME="<eth-username>"
export INSTITUTIONAL_PASSWORD="<eth-password>"
# Optional overrides
export INSTITUTIONAL_PUBLISHER="ieee"
export INSTITUTIONAL_HEADLESS=false
export INSTITUTIONAL_TIMEOUT_MS=180000
```

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

To run continuous maintenance sweeps, use the scheduler helper:

```bash
scripts/run_scheduler.py
```
Adjust the interval via `MAINTENANCE_INTERVAL_SECONDS` as needed.

---

For automated setup, see `scripts/bootstrap_env.sh`.
