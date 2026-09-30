#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT_DIR}/.venv311/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Missing ${PYTHON}. Create the Python 3.11 environment first."
  exit 1
fi

if [[ ! -x "${ROOT_DIR}/frontend/node_modules/.bin/tsc" ]]; then
  echo "Missing frontend dependencies. Run: npm install --prefix frontend"
  exit 1
fi

cd "${ROOT_DIR}"

echo "Checking backend Python modules..."
PYTHONPATH=backend "${PYTHON}" -m compileall -q backend/app

echo "Building frontend..."
npm run build --prefix frontend

echo "Complete build succeeded."
