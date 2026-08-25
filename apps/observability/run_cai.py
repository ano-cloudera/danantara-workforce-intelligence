#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path


def resolve_application_dir(app_name: str) -> Path:
    script_path = globals().get("__file__")
    if script_path:
        return Path(script_path).resolve().parent
    cwd = Path.cwd().resolve()
    project_dir = os.getenv("CDSW_PROJECT_DIR")
    candidates = ([Path(project_dir).resolve()] if project_dir else []) + [cwd]
    for base in candidates:
        for candidate in (base / "apps" / app_name, base):
            if (candidate / "run_cai.py").is_file():
                return candidate
        for candidate in base.glob(f"*/apps/{app_name}"):
            if (candidate / "run_cai.py").is_file():
                return candidate
    raise RuntimeError(
        f"Unable to locate apps/{app_name}; start the CAI Application from project root"
    )


HERE = resolve_application_dir("observability")
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
        pip_env = os.environ.copy()
        pip_env.pop("PIP_USER", None)
        pip_env.pop("PYTHONUSERBASE", None)
        subprocess.check_call(
            [str(py), "-m", "pip", "--isolated", "install", "--no-user", "--upgrade", "pip"],
            env=pip_env,
        )
        subprocess.check_call(
            [
                str(py),
                "-m",
                "pip",
                "--isolated",
                "install",
                "--no-user",
                "-r",
                str(HERE / "requirements.txt"),
            ],
            env=pip_env,
        )
        MARKER.touch()
    return py


def run_application(py: Path, host: str, port: int) -> None:
    command = [str(py), "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)]
    print(f"Starting observability host={host} port={port}", flush=True)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Observability exited with status {result.returncode}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-port", type=int, default=LOCAL_OBSERVABILITY_PORT)
    args = parser.parse_args() if globals().get("__file__") else parser.parse_known_args()[0]
    py = ensure_venv()
    port = resolve_app_port(args.local_port)
    host = resolve_bind_host()
    os.chdir(HERE)
    run_application(py, host, port)


if __name__ == "__main__":
    main()
