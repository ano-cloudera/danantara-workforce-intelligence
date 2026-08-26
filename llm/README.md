# Ray + vLLM multi-GPU serving on Cloudera AI Workbench

PoC/reference deployment for Cloudera AI Workbench with resource:

- 4x NVIDIA A10G 24 GB
- minimum 8 vCPU for the Application
- minimum 32 GiB RAM for the Application
- Python 3.10 NVIDIA GPU Runtime

Target architecture:

```text
1 CAI Application
└── 1 single-node Ray cluster
    ├── LLM deployment: Qwen3-14B via vLLM, tensor_parallel_size=2 (2 whole A10G GPUs)
    └── Embedding deployment: BAAI/bge-m3, 2 replicas x 1 whole A10G GPU each
```

Total: 4 GPUs. This is whole-GPU allocation with vLLM tensor parallelism for
the LLM, not the fractional soft-GPU-sharing pattern used in the earlier
single-L4 PoC (`app.py`, still kept here as a reference for that pattern).

## Model choices

- **LLM: `Qwen/Qwen3-14B`.** In BF16 this needs ~28 GB of weights alone, which
  does not fit on a single 24 GB A10G. `tensor_parallel_size=2` shards the
  model across 2 GPUs (~14 GB/GPU), leaving comfortable headroom per GPU for
  KV cache and concurrent requests. Qwen3-14B has 40 attention heads / 8 KV
  heads, both divisible by 2 and 4, so TP=2 or TP=4 are both technically
  valid — TP=2 is used here to avoid unnecessary cross-GPU NCCL overhead for
  a model this size, keeping the other 2 GPUs free for embeddings.
- **Embedding: `BAAI/bge-m3`.** Strong multilingual dense retrieval quality,
  8192-token context, good default for RAG-style workloads. Runs as 2
  independent replicas on 2 dedicated GPUs so embedding traffic never
  contends with LLM traffic.
- FP8 quantization is intentionally avoided: A10G (compute capability 8.6,
  Ampere) does not get FP8 acceleration in vLLM, which requires Ada/Hopper+.
  Use BF16 (default) or AWQ/GPTQ INT4 if you need to fit the LLM on fewer
  GPUs.

## Stage 1: Create project

1. Create a new project, e.g. `ray-a10g-poc`.
2. Upload the project source to the project.
3. Extract if needed and `cd` into the project directory.

## Stage 2: Create a Session for setup

Use:

| Resource | Value |
|---|---:|
| Runtime | Python 3.10 NVIDIA GPU Edition |
| CPU | 8 vCPU |
| Memory | 32 GiB |
| GPU | 2x NVIDIA A10G (enough to smoke-test the LLM download/load path) |

Run:

```bash
bash setup.sh
source .venv-ray-l4/bin/activate
python check_env.py
python download_model.py
```

Expected versions:

```text
Ray: 2.43.0
vLLM: 0.8.5
Torch: 2.6.0
GPU: NVIDIA A10G
```

After the download finishes, confirm both model directories are present:

```bash
test -f models/qwen3-14b/config.json && echo "LLM MODEL READY"
test -f models/bge-m3/config.json && echo "EMBEDDING MODEL READY"
```

Stop the Session before starting the Application if your project only has 4
total GPUs available — Sessions and Applications compete for the same GPU
quota.

## Stage 3: Create the CAI Application

Use configuration:

| Field | Value |
|---|---|
| Name | `ray-a10g-multimodel` |
| Script | `launch_cai.py` |
| Kernel | Python 3 |
| Runtime | Same runtime as the Session |
| CPU | 8 vCPU |
| Memory | 32 GiB |
| GPU | 4x NVIDIA A10G |

Default Application environment (already baked into `launch_cai.py`, override
via Application Environment Variables if needed):

```text
LLM_MODEL_ID=Qwen/Qwen3-14B
LLM_MODEL_DIR=/home/cdsw/<project>/models/qwen3-14b
EMBED_MODEL_ID=BAAI/bge-m3
EMBED_MODEL_DIR=/home/cdsw/<project>/models/bge-m3
LLM_TENSOR_PARALLEL_SIZE=2
LLM_GPU_MEMORY_UTILIZATION=0.90
EMBED_NUM_REPLICAS=2
EMBED_GPU_PER_REPLICA=1.0
MAX_MODEL_LEN=8192
MAX_NUM_SEQS=16
DTYPE=bfloat16
```

Do not set `CDSW_APP_PORT`; it is provided automatically by Cloudera AI.

The Application exposes:

```text
/
/health
/v1/chat/completions
/v1/embeddings
```

First startup can take several minutes: Qwen3-14B weights must load and
shard across 2 GPUs, and the embedding replicas must initialize on the
other 2.

If the Application pod cannot be created at all, the problem is upstream of
Ray. Check A10G GPU availability, resource profile/quota, and Kubernetes
events from Cloudera AI.

## Stage 4: Test from the terminal

```bash
source .venv-ray-l4/bin/activate
python load_test.py \
  --base-url http://127.0.0.1:${CDSW_APP_PORT:-8080} \
  --requests 12 \
  --concurrency 4
```

Chat completion:

```bash
curl -s http://127.0.0.1:${CDSW_APP_PORT:-8080}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Say hi in one sentence."}],"max_tokens":64}'
```

Embeddings:

```bash
curl -s http://127.0.0.1:${CDSW_APP_PORT:-8080}/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"input":["contoh teks untuk di-embed"]}'
```

## Troubleshooting

### Ray does not see 4 GPUs

Stop the Application, confirm GPU availability, then check the Application
resource profile requests 4x NVIDIA A10G.

### CUDA out of memory on the LLM deployment

Lower `LLM_GPU_MEMORY_UTILIZATION` (e.g. `0.70`), or reduce `MAX_MODEL_LEN`
and `MAX_NUM_SEQS`. If it still does not fit, switch `LLM_TENSOR_PARALLEL_SIZE`
to `4` (all GPUs to the LLM) and drop `EMBED_NUM_REPLICAS` to `0`/move
embedding serving off-GPU.

### vLLM fails to import Qwen3 architecture / "unsupported architecture"

This means `vllm` is older than 0.8.4 (Qwen3 support was added in vLLM
0.8.4). Re-run `bash setup.sh` to reinstall pinned versions from
`requirements.txt`, and confirm with `python check_env.py`.

### Package conflict

The Application must use `launch_cai.py`. That launcher runs Python from
`.venv-ray-l4`, not the runtime's global packages.

If setup shows `Can not perform a '--user' install`, re-run:

```bash
PIP_USER=0 bash setup.sh
```
