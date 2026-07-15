#!/usr/bin/env bash
set -euo pipefail

cleanup() {
  kill "${BACKEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run uvicorn seglabeler.api:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
npm --prefix frontend run dev
