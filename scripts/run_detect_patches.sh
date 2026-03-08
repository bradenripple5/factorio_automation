#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="${ROOT_DIR}/env/bin/activate"

if [[ ! -f "${VENV_PATH}" ]]; then
  echo "Virtualenv not found at ${VENV_PATH}"
  echo "Create it with: python -m venv env && source env/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# Activate venv and run the detector in this shell.
source "${VENV_PATH}"

# Ensure dependencies are installed.
python -m pip install -r "${ROOT_DIR}/requirements.txt" >/dev/null

if [[ $# -eq 0 ]]; then
  SCREENSHOT_DIR="${HOME}/Pictures/Screenshots"
  LATEST_SCREENSHOT="$(ls -t "${SCREENSHOT_DIR}"/*.png 2>/dev/null | head -n 1 || true)"
  if [[ -z "${LATEST_SCREENSHOT}" ]]; then
    echo "No screenshots found in ${SCREENSHOT_DIR}"
    exit 1
  fi
  python "${ROOT_DIR}/scripts/detect_patches.py" "${LATEST_SCREENSHOT}" --auto-crop --center-zero --overlay
else
  python "${ROOT_DIR}/scripts/detect_patches.py" "$@"
fi
