#!/usr/bin/env bash
# Local dev launcher. Reads .env if present.
set -euo pipefail
cd "$(dirname "$0")"

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -r requirements.txt

if [ -f .env ]; then set -a; source .env; set +a; fi
exec streamlit run dashboard.py
