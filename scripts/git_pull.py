#!/usr/bin/env python3
"""CAI Job: fast-forward this Workbench project's git checkout from origin/main.

Refuses to run if there are local uncommitted changes, so it never discards
in-progress edits made directly in a CAI session.
"""

import os
import subprocess
import sys
from pathlib import Path


def resolve_project_root() -> Path:
    script_path = globals().get("__file__")
    if script_path:
        return Path(script_path).resolve().parents[1]
    if os.getenv("CDSW_PROJECT_DIR"):
        return Path(os.environ["CDSW_PROJECT_DIR"]).resolve()
    return Path.cwd().resolve()


ROOT = resolve_project_root()


def run(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def main() -> None:
    status = run("status", "--porcelain")
    if status:
        print(status)
        raise SystemExit(
            "Uncommitted local changes present; refusing to pull. "
            "Commit, stash, or discard them first."
        )

    branch = run("rev-parse", "--abbrev-ref", "HEAD")
    run("fetch", "origin", branch)
    before = run("rev-parse", "HEAD")
    print(run("merge", "--ff-only", f"origin/{branch}"))
    after = run("rev-parse", "HEAD")

    if before == after:
        print(f"Already up to date at {before[:12]} ({branch})")
    else:
        print(f"Updated {before[:12]} -> {after[:12]} ({branch})")


if __name__ == "__main__":
    main()
