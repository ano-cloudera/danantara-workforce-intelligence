#!/usr/bin/env python3
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys


def run(command):
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "command not found"


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


print("Python:", sys.version.replace("\n", " "))
print("Platform:", platform.platform())
print("Executable:", sys.executable)
print("Ray:", package_version("ray"))
print("vLLM:", package_version("vllm"))
print("Torch:", package_version("torch"))
print("CUDA_VISIBLE_DEVICES:", os.getenv("CUDA_VISIBLE_DEVICES", "not set"))
print("CDSW_APP_PORT:", os.getenv("CDSW_APP_PORT", "not set; local default is 8080"))
print("Disk:", shutil.disk_usage("."))
print("/dev/shm:", shutil.disk_usage("/dev/shm") if os.path.exists("/dev/shm") else "missing")
print("\nnvidia-smi -L")
print(run(["nvidia-smi", "-L"]))
print("\nnvidia-smi summary")
print(
    run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader",
        ]
    )
)
