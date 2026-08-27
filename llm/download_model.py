#!/usr/bin/env python3
import os
from pathlib import Path

from huggingface_hub import snapshot_download


LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "Qwen/Qwen3-14B-AWQ")
LLM_MODEL_DIR = Path(os.getenv("LLM_MODEL_DIR", "./models/qwen3-14b-awq")).resolve()
EMBED_MODEL_ID = os.getenv("EMBED_MODEL_ID", "BAAI/bge-m3")
EMBED_MODEL_DIR = Path(os.getenv("EMBED_MODEL_DIR", "./models/bge-m3")).resolve()


def download(model_id: str, model_dir: Path):
    model_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {model_id}")
    print(f"Destination: {model_dir}")
    snapshot_download(
        repo_id=model_id,
        local_dir=str(model_dir),
        token=os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or None,
        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
    )
    if not (model_dir / "config.json").exists():
        raise RuntimeError(f"Download finished but config.json was not found in {model_dir}")
    print(f"Model download verified: {model_id}")


def main():
    download(LLM_MODEL_ID, LLM_MODEL_DIR)
    download(EMBED_MODEL_ID, EMBED_MODEL_DIR)


if __name__ == "__main__":
    main()
