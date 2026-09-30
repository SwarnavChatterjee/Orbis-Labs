#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PYTHON="${ROOT_DIR}/.venv311/bin/python"
BACKEND_UVICORN="${ROOT_DIR}/.venv311/bin/uvicorn"
BACKEND_PROCRASTINATE="${ROOT_DIR}/.venv311/bin/procrastinate"
FRONTEND_DIR="${ROOT_DIR}/frontend"

if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  echo "Missing ${BACKEND_PYTHON}. Create the Python 3.11 environment first."
  exit 1
fi

if [[ ! -x "${FRONTEND_DIR}/node_modules/.bin/vite" ]]; then
  echo "Missing frontend dependencies. Run: npm install --prefix frontend"
  exit 1
fi

cd "${ROOT_DIR}"

echo "Starting PostgreSQL..."
docker compose up -d postgres

echo "Applying database migrations..."
PYTHONPATH=backend "${ROOT_DIR}/.venv311/bin/alembic" -c backend/alembic.ini upgrade head
PYTHONPATH=backend "${BACKEND_PYTHON}" -m procrastinate -a app.jobs.tasks.procrastinate_app schema --apply

cleanup() {
  trap - EXIT INT TERM
  [[ -n "${FRONTEND_PID:-}" ]] && kill "${FRONTEND_PID}" 2>/dev/null || true
  [[ -n "${WORKER_PID:-}" ]] && kill "${WORKER_PID}" 2>/dev/null || true
  [[ -n "${API_PID:-}" ]] && kill "${API_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting API on http://127.0.0.1:8000..."
PYTHONPATH=backend "${BACKEND_UVICORN}" app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

echo "Starting query worker..."
PYTHONPATH=backend "${BACKEND_PROCRASTINATE}" -a app.jobs.tasks.procrastinate_app worker --queues queries --wait &
WORKER_PID=$!

echo "Starting frontend on http://127.0.0.1:5173..."
(cd "${FRONTEND_DIR}" && npm run dev -- --host 127.0.0.1) &
FRONTEND_PID=$!

echo
echo "Orbis Labs is running at http://127.0.0.1:5173"
echo "Press Ctrl+C to stop the API, worker, and frontend."
wait
