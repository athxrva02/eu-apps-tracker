#!/bin/sh
set -eu
umask 077

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_root"
export PYTHONPATH="$repo_root/backend"

if [ ! -x .venv/bin/python ]; then
  printf '%s\n' 'Python dependencies are missing. Run make install first.' >&2
  exit 1
fi
if [ ! -f .env ]; then
  printf '%s\n' 'Create a private .env using .env.example before starting.' >&2
  exit 1
fi
if [ ! -f frontend/dist/index.html ]; then
  npm --prefix frontend ci --no-audit --no-fund
  npm --prefix frontend run build
fi

.venv/bin/python -m app.bootstrap
.venv/bin/python -m app.worker &
worker_pid=$!
cleanup() {
  kill "$worker_pid" 2>/dev/null || true
  wait "$worker_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM

printf '%s\n' 'Starting Fieldwork at http://localhost:8000' 'Keep this terminal open. Press Ctrl+C to stop the web app and worker.'
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
