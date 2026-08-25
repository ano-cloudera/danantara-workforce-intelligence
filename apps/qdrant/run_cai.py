#!/usr/bin/env python3
import argparse
import os
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
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
    raise RuntimeError(
        f"Unable to locate apps/{app_name}; start the CAI Application from project root"
    )


HERE = resolve_application_dir("qdrant")
ROOT = HERE.parents[1]
RUNTIME = HERE / ".runtime"
BIN_DIR = HERE / "bin"

sys.path.insert(0, str(ROOT))

from config.cai_runtime import (  # noqa: E402
    LOCAL_QDRANT_PORT,
    resolve_app_port,
    resolve_bind_host,
)


def download_binary(version: str) -> Path:
    local = BIN_DIR / "qdrant"
    if local.exists():
        return local
    target = RUNTIME / version / "qdrant"
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    arch = platform.machine().lower()
    triple = (
        "x86_64-unknown-linux-gnu" if arch in ("x86_64", "amd64") else "aarch64-unknown-linux-gnu"
    )
    url = (
        os.getenv("QDRANT_DOWNLOAD_URL")
        or f"https://github.com/qdrant/qdrant/releases/download/v{version}/qdrant-{triple}.tar.gz"
    )
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "qdrant.tar.gz"
        urllib.request.urlretrieve(url, archive)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(td)
        found = next((p for p in Path(td).rglob("qdrant") if p.is_file()), None)
        if not found:
            raise RuntimeError("Qdrant binary not found in downloaded archive")
        shutil.copy2(found, target)
    target.chmod(target.stat().st_mode | stat.S_IEXEC)
    return target


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--local-port", type=int, default=LOCAL_QDRANT_PORT)
    a = p.parse_args() if globals().get("__file__") else p.parse_known_args()[0]
    version = os.getenv("QDRANT_VERSION", "1.19.0")
    binary = download_binary(version)
    port = resolve_app_port(a.local_port)
    os.environ["QDRANT__SERVICE__HOST"] = resolve_bind_host()
    os.environ["QDRANT__SERVICE__HTTP_PORT"] = str(port)
    storage_path = Path(os.getenv("QDRANT_STORAGE_PATH", str(ROOT / "data" / "qdrant-storage")))
    if not storage_path.is_absolute():
        storage_path = ROOT / storage_path
    os.environ["QDRANT__STORAGE__STORAGE_PATH"] = str(storage_path)
    if os.getenv("QDRANT_API_KEY"):
        os.environ["QDRANT__SERVICE__API_KEY"] = os.getenv("QDRANT_API_KEY")
    os.execv(str(binary), [str(binary)])


if __name__ == "__main__":
    main()
