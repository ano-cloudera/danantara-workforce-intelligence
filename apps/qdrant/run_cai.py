#!/usr/bin/env python3
import argparse
import os
import platform
import shutil
import stat
import subprocess
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
    # CAI may execute this source as notebook/interpreter code without __file__,
    # CDSW_PROJECT_DIR, or a repository working directory. Qdrant's launcher is
    # intentionally able to bootstrap its binary and storage from that cwd.
    return cwd


HERE = resolve_application_dir("qdrant")
ROOT = (
    HERE.parents[1]
    if HERE.name == "qdrant" and HERE.parent.name == "apps"
    else Path(os.getenv("CDSW_PROJECT_DIR", str(HERE))).resolve()
)
RUNTIME = HERE / ".runtime"
BIN_DIR = HERE / "bin"

LOCAL_QDRANT_PORT = 6333
CAI_BIND_HOST = "127.0.0.1"


def resolve_app_port(local_default: int) -> int:
    return int(os.getenv("CDSW_APP_PORT") or os.getenv("PORT") or local_default)


def resolve_bind_host() -> str:
    return CAI_BIND_HOST


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


def validate_binary(binary: Path) -> str:
    try:
        result = subprocess.run(
            [str(binary), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Qdrant binary cannot execute on {platform.machine()}: {binary}: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Qdrant binary version probe timed out: {binary}") from exc
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(
            f"Qdrant binary probe failed with status {result.returncode}: {output or binary}"
        )
    return output


def run_qdrant(binary: Path) -> None:
    try:
        result = subprocess.run([str(binary)], check=False)
    except OSError as exc:
        raise RuntimeError(f"Qdrant failed to start: {binary}: {exc}") from exc
    if result.returncode != 0:
        raise RuntimeError(f"Qdrant exited with status {result.returncode}")


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
    binary_version = validate_binary(binary)
    print(
        "Starting Qdrant",
        f"binary={binary}",
        f"version={binary_version}",
        f"architecture={platform.machine()}",
        f"host={os.environ['QDRANT__SERVICE__HOST']}",
        f"port={port}",
        f"storage={storage_path}",
        flush=True,
    )
    run_qdrant(binary)


if __name__ == "__main__":
    main()
