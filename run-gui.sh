#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="python"
fi

cd "${PROJECT_DIR}"

if ! "${PYTHON_BIN}" -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter/Tk is not available for ${PYTHON_BIN}." >&2
  echo "Install the system Tk runtime before starting the GUI." >&2
  exit 1
fi

exec "${PYTHON_BIN}" main.py
