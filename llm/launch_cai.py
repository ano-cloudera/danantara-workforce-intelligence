#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path


def find_package_dir() -> Path:
    """Find the project folder in both CAI Session and Application runtimes."""
    candidates = []
    script_file = globals().get("__file__")
    if script_file:
        candidates.append(Path(script_file).resolve().parent)

    candidates.extend(
        [
            Path.cwd() / "ray-l4-cai-poc",
            Path("/home/cdsw/ray-l4-cai-poc"),
            Path.cwd(),
        ]
    )

    for candidate in candidates:
        if (candidate / "multimodel_app.py").is_file():
            return candidate.resolve()

    checked = "\n  - ".join(str(path) for path in candidates)
    raise SystemExit(f"Cannot find ray-l4-cai-poc. Checked:\n  - {checked}")


def main():
    package_dir = find_package_dir()
    python = package_dir / ".venv-ray-l4" / "bin" / "python"
    app = package_dir / "multimodel_app.py"

    if not python.is_file():
        raise SystemExit(
            f"Ray environment is missing at {python}. "
            "Open a GPU CAI Session and run: "
            "cd /home/cdsw/ray-l4-cai-poc && PIP_USER=0 bash setup.sh"
        )

    env = os.environ.copy()
    env.setdefault("LLM_MODEL_ID", "Qwen/Qwen3-14B")
    env.setdefault("LLM_MODEL_DIR", str(package_dir / "models" / "qwen3-14b"))
    env.setdefault("EMBED_MODEL_ID", "BAAI/bge-m3")
    env.setdefault("EMBED_MODEL_DIR", str(package_dir / "models" / "bge-m3"))
    env.setdefault("LLM_TENSOR_PARALLEL_SIZE", "2")
    env.setdefault("LLM_GPU_MEMORY_UTILIZATION", "0.90")
    env.setdefault("EMBED_NUM_REPLICAS", "2")
    env.setdefault("EMBED_GPU_PER_REPLICA", "1.0")
    env.setdefault("MAX_MODEL_LEN", "8192")
    env.setdefault("MAX_NUM_SEQS", "16")
    env.setdefault("DTYPE", "bfloat16")
    env.setdefault("TOKENIZERS_PARALLELISM", "false")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PIP_USER", "0")
    env.setdefault("RAY_DEDUP_LOGS", "0")

    print(f"Package directory : {package_dir}", flush=True)
    print(f"Python environment: {python}", flush=True)
    print(f"LLM model directory     : {env['LLM_MODEL_DIR']}", flush=True)
    print(f"Embedding model directory: {env['EMBED_MODEL_DIR']}", flush=True)
    print("Starting Ray + vLLM Application...", flush=True)

    process = subprocess.Popen(
        [str(python), "-u", str(app)],
        cwd=str(package_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[RAY-APP] {line}", end="", flush=True)

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Ray application stopped with exit code {return_code}")


if __name__ == "__main__":
    main()
