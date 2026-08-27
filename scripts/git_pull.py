#!/usr/bin/env python3
"""CAI Job: run `git pull` in this Workbench project's checkout."""

import os
import subprocess
from pathlib import Path


REPO_DIR_NAME = "danantara-workforce-intelligence"


def resolve_project_root() -> Path:
    script_path = globals().get("__file__")
    if script_path:
        candidate = Path(script_path).resolve().parents[1]
        if (candidate / ".git").exists():
            return candidate
    if os.getenv("CDSW_PROJECT_DIR"):
        candidate = Path(os.environ["CDSW_PROJECT_DIR"]).resolve()
        if (candidate / ".git").exists():
            return candidate
    named_candidate = Path.home() / REPO_DIR_NAME
    if (named_candidate / ".git").exists():
        return named_candidate
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
