#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_PATH="$REPO_ROOT/.venv"

if [[ ! -d "$VENV_PATH" ]]; then
  python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"

pip install --upgrade pip
pip install -r "$REPO_ROOT/requirements.txt"

# Install Playwright browsers used by institutional automation
if command -v playwright >/dev/null 2>&1; then
  playwright install firefox chromium webkit
else
  echo "Playwright CLI not found in PATH. Install it with 'pip install playwright' before running this script." >&2
fi

echo "Environment ready. Activate with: source $VENV_PATH/bin/activate"
