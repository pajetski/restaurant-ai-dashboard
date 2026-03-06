#!/usr/bin/env bash
set -euo pipefail

APP_FILE="dashboard.py"
VENV_DIR=".venv"

cd "$(dirname "$0")"

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null
python -m pip install -q streamlit pandas requests

echo "Launching Streamlit..."
exec streamlit run "$APP_FILE"

