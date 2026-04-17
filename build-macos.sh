#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="python"
fi

if ! "${PYTHON_BIN}" -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter/Tk is not available for ${PYTHON_BIN}." >&2
  echo "Install the system Tk runtime before building the macOS GUI binary." >&2
  exit 1
fi

mkdir -p "${PROJECT_DIR}/packages/macos"

"${PYTHON_BIN}" -m PyInstaller --noconfirm --clean --onefile --windowed \
  --name "MikroTik Config Generator" \
  --add-data "templates:templates" \
  main.py

cd "${PROJECT_DIR}/dist"
zip -r "../packages/macos/mikrotik-config-generator-macos.zip" "MikroTik Config Generator"

echo "macOS package created at: ${PROJECT_DIR}/packages/macos/mikrotik-config-generator-macos.zip"
