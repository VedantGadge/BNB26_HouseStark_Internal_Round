#!/bin/sh
set -eu

python -m app.worker &
worker_pid=$!

shutdown() {
  kill "$worker_pid" 2>/dev/null || true
  wait "$worker_pid" 2>/dev/null || true
}

trap shutdown EXIT INT TERM

uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}"
