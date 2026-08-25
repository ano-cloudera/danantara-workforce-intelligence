#!/usr/bin/env python3
import argparse
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME = HERE / ".runtime"
BIN_DIR = HERE / "bin"


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
    p.add_argument("--local-port", type=int, default=6333)
    a = p.parse_args()
    version = os.getenv("QDRANT_VERSION", "1.19.0")
    binary = download_binary(version)
    port = os.getenv("CDSW_APP_PORT") or os.getenv("CML_APP_PORT") or str(a.local_port)
    os.environ["QDRANT__SERVICE__HOST"] = os.getenv("APP_BIND_HOST", "127.0.0.1")
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
