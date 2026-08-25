#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VENV = HERE / ".venv-observability"
MARKER = VENV / ".requirements-installed"

sys.path.insert(0, str(ROOT))

from config.cai_runtime import (  # noqa: E402
    LOCAL_OBSERVABILITY_PORT,
    resolve_app_port,
    resolve_bind_host,
)


def ensure_venv():
    if not VENV.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    py = VENV / "bin" / "python"
    if not MARKER.exists() or (HERE / "requirements.txt").stat().st_mtime > MARKER.stat().st_mtime:
        subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call(
            [str(py), "-m", "pip", "install", "-r", str(HERE / "requirements.txt")]
        )
        MARKER.touch()
    return py


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-port", type=int, default=LOCAL_OBSERVABILITY_PORT)
    args = parser.parse_args()
    py = ensure_venv()
    port = resolve_app_port(args.local_port)
    host = resolve_bind_host()
    os.chdir(HERE)
    os.execv(
        str(py),
        [str(py), "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
    )


if __name__ == "__main__":
    main()
