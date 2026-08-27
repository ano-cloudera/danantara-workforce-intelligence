#!/usr/bin/env python3
"""CAI Job: fast-forward this Workbench project's git checkout from origin/main.

Refuses to run if there are local uncommitted changes, so it never discards
in-progress edits made directly in a CAI session.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
