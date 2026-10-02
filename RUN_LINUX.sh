#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8080
