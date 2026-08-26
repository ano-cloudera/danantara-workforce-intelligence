#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-.venv-ray-l4}"

# Cloudera AI runtimes can set PIP_USER for global session installs.
# A virtual environment must not install into the user site-packages directory.
unset PIP_USER || true
export PIP_USER=0

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip --isolated install --upgrade pip uv
"$VENV_DIR/bin/uv" pip install --python "$VENV_DIR/bin/python" -r requirements.txt
"$VENV_DIR/bin/python" -m pip check

echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
