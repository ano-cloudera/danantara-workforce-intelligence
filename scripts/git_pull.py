#!/usr/bin/env python3
"""CAI Job: run `git pull` in this Workbench project's checkout."""

import os
import subprocess
from pathlib import Path


def resolve_project_root() -> Path:
    script_path = globals().get("__file__")
    if script_path:
        return Path(script_path).resolve().parents[1]
    if os.getenv("CDSW_PROJECT_DIR"):
        return Path(os.environ["CDSW_PROJECT_DIR"]).resolve()
    return Path.cwd().resolve()


def main() -> None:
    root = resolve_project_root()
    print(f"Running git pull in {root}")
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
