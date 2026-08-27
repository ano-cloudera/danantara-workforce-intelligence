#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def resolve_job_dir() -> Path:
    script_path = globals().get("__file__")
    if script_path:
        return Path(script_path).resolve().parent
    bases = [Path.cwd().resolve()]
    if os.getenv("CDSW_PROJECT_DIR"):
        bases.insert(0, Path(os.environ["CDSW_PROJECT_DIR"]).resolve())
    for base in bases:
        candidates = [base / "jobs" / "cv_ingestion", base]
        candidates.extend(base.glob("*/jobs/cv_ingestion"))
        for candidate in candidates:
            if (candidate / "run_job.py").is_file():
                return candidate
    raise RuntimeError("Unable to locate jobs/cv_ingestion from the CAI project")


HERE = resolve_job_dir()
VENV = HERE / ".venv-cv-ingestion"
MARKER = VENV / ".requirements-installed"


def ensure_venv() -> Path:
    if not VENV.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    py = VENV / "bin" / "python"
    requirements = HERE / "requirements.txt"
    if not MARKER.exists() or requirements.stat().st_mtime > MARKER.stat().st_mtime:
        pip_env = os.environ.copy()
        pip_env.pop("PIP_USER", None)
        pip_env.pop("PYTHONUSERBASE", None)
        subprocess.check_call(
            [str(py), "-m", "pip", "--isolated", "install", "--no-user", "-r", str(requirements)],
            env=pip_env,
        )
        MARKER.touch()
    return py


def main() -> None:
    initialize = os.getenv("CV_JOB_INIT_SCHEMA", "false").lower() == "true"
    script = "init_schema.py" if initialize else "run_job.py"
    command = [str(ensure_venv()), str(HERE / script)]
    if not initialize and os.getenv("CV_JOB_DRY_RUN", "false").lower() == "true":
        command.append("--dry-run")
    subprocess.check_call(command, cwd=HERE)


if __name__ == "__main__":
    main()
