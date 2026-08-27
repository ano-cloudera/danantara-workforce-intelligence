#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-.venv-ray-l4}"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Virtual environment not found. Run: bash setup.sh"
  exit 1
fi

export LLM_MODEL_ID="${LLM_MODEL_ID:-Qwen/Qwen3-14B-AWQ}"
export LLM_MODEL_DIR="${LLM_MODEL_DIR:-./models/qwen3-14b-awq}"
export EMBED_MODEL_ID="${EMBED_MODEL_ID:-BAAI/bge-m3}"
export EMBED_MODEL_DIR="${EMBED_MODEL_DIR:-./models/bge-m3}"
export LLM_TENSOR_PARALLEL_SIZE="${LLM_TENSOR_PARALLEL_SIZE:-1}"
export LLM_QUANTIZATION="${LLM_QUANTIZATION:-awq_marlin}"
export LLM_GPU_MEMORY_UTILIZATION="${LLM_GPU_MEMORY_UTILIZATION:-0.90}"
export EMBED_NUM_REPLICAS="${EMBED_NUM_REPLICAS:-1}"
export EMBED_GPU_PER_REPLICA="${EMBED_GPU_PER_REPLICA:-1.0}"
export MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
export MAX_NUM_SEQS="${MAX_NUM_SEQS:-16}"
export DTYPE="${DTYPE:-auto}"
export TOKENIZERS_PARALLELISM=false

exec "$VENV_DIR/bin/python" multimodel_app.py
