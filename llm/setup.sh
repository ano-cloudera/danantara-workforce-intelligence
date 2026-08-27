#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-.venv-ray-l4}"

# Cloudera AI ML Runtime images ship /etc/pip.conf with `install.user = true`,
# which pip config files take precedence over the PIP_USER env var. A
# virtual environment must not install into user site-packages, so force
# --no-user explicitly on every pip invocation instead of relying on env vars.
unset PIP_USER || true
export PIP_USER=0

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip --isolated install --no-user --upgrade pip uv
"$VENV_DIR/bin/uv" pip install --python "$VENV_DIR/bin/python" -r requirements.txt

# ray[default] pulls in opencensus for the dashboard agent's metrics
# exporter. opencensus's protobuf-generated stubs require protobuf>=5.26,
# which conflicts with the protobuf<5 pin Ray Serve itself needs
# (ray-project/ray#54849). Uninstalling opencensus cleanly (a real
# ModuleNotFoundError, not a broken import) makes Ray's dashboard agent
# fall back to minimal mode and skip metrics export instead of crashing
# the whole raylet.
"$VENV_DIR/bin/python" -m pip uninstall -y --no-input opencensus opencensus-context || true

"$VENV_DIR/bin/python" -m pip check

echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
