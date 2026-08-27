# Ray + vLLM multi-GPU serving on Cloudera AI Workbench

PoC/reference deployment for Cloudera AI Workbench with resource:

- 2x NVIDIA A10G 24 GB
- minimum 8 vCPU for the Application
- minimum 32 GiB RAM for the Application
- Python 3.10 NVIDIA GPU Runtime

Target architecture:

```text
1 CAI Application
└── 1 single-node Ray cluster
    ├── LLM deployment: Qwen3-14B-AWQ via vLLM, tensor_parallel_size=1 (1 whole A10G GPU)
    └── Embedding deployment: BAAI/bge-m3, 1 replica x 1 whole A10G GPU
```

Total: 2 GPUs. Both deployments get one dedicated whole GPU each — no
tensor parallelism, no embedding replication, no fractional soft-GPU-sharing
(the pattern used in the earlier single-L4 PoC, `app.py`, still kept here as
a reference for that pattern).

## Model choices

- **LLM: `Qwen/Qwen3-14B-AWQ`.** The BF16 checkpoint needs ~28 GB of weights
  alone, which does not fit on a single 24 GB A10G, and this deployment
  intentionally uses `tensor_parallel_size=1` (no sharding across GPUs) so
  the LLM and embedding model each get one independent, dedicated GPU. The
  AWQ INT4 quantized checkpoint is ~10 GB, comfortably fitting on one A10G
  with headroom for KV cache and concurrent requests. vLLM auto-selects the
  `awq_marlin` kernel, which is Ampere-compatible (sm_80+, covers A10G's
  sm_86). Quality is slightly lower than BF16 due to INT4 quantization, but
  the gap is typically small for chat/completion workloads.
- **Embedding: `BAAI/bge-m3`.** Strong multilingual dense retrieval quality,
  8192-token context, good default for RAG-style workloads. Runs as a single
  replica on its own dedicated GPU so embedding traffic never contends with
  LLM traffic (no autoscaling/replication — add `EMBED_NUM_REPLICAS` back if
  you later have a spare GPU for it).
- FP8 quantization is intentionally avoided: A10G (compute capability 8.6,
  Ampere) does not get FP8 acceleration in vLLM, which requires Ada/Hopper+.
  AWQ INT4 (via Marlin kernels) is the correct quantization choice on
  Ampere.

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
| GPU | 2x NVIDIA A10G |

Run:

```bash
PIP_USER=0 bash setup.sh
source .venv-ray-l4/bin/activate
python check_env.py
python download_model.py
```

Expected versions:

```text
Ray: 2.48.0
vLLM: 0.9.2
Torch: 2.7.0
GPU: NVIDIA A10G
```

After the download finishes, confirm both model directories are present:

```bash
test -f models/qwen3-14b-awq/config.json && echo "LLM MODEL READY"
test -f models/bge-m3/config.json && echo "EMBEDDING MODEL READY"
```

Stop the Session before starting the Application — Sessions and Applications
compete for the same GPU quota.

## Stage 3: Create the CAI Application

Use configuration:

| Field | Value |
|---|---|
| Name | `ray-a10g-multimodel` |
| Script | `llm/launch_cai.py` |
| Kernel | Python 3 |
| Runtime | Same runtime as the Session |
| CPU | 8 vCPU |
| Memory | 32 GiB |
| GPU | 2x NVIDIA A10G |

Default Application environment (already baked into `launch_cai.py`, override
via Application Environment Variables if needed):

```text
LLM_MODEL_ID=Qwen/Qwen3-14B-AWQ
LLM_MODEL_DIR=/home/cdsw/<project>/models/qwen3-14b-awq
EMBED_MODEL_ID=BAAI/bge-m3
EMBED_MODEL_DIR=/home/cdsw/<project>/models/bge-m3
LLM_TENSOR_PARALLEL_SIZE=1
LLM_QUANTIZATION=awq_marlin
LLM_GPU_MEMORY_UTILIZATION=0.90
EMBED_NUM_REPLICAS=1
EMBED_GPU_PER_REPLICA=1.0
MAX_MODEL_LEN=8192
MAX_NUM_SEQS=16
DTYPE=auto
```

Do not set `CDSW_APP_PORT`; it is provided automatically by Cloudera AI.

The Application exposes:

```text
/
/health
/v1/chat/completions
/v1/embeddings
```

First startup can take a few minutes while Qwen3-14B-AWQ and BGE-M3 load
onto their respective GPUs.

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

### Ray does not see 2 GPUs

Stop the Application, confirm GPU availability, then check the Application
resource profile requests 2x NVIDIA A10G.

### CUDA out of memory on the LLM deployment

Lower `LLM_GPU_MEMORY_UTILIZATION` (e.g. `0.80`), or reduce `MAX_MODEL_LEN`
and `MAX_NUM_SEQS`.

### vLLM fails to import Qwen3 architecture / "unsupported architecture"

This means `vllm` predates Qwen3 support (added in vLLM 0.8.4; this project
pins a later, more stable release for Qwen3+AWQ). Re-run `bash setup.sh` to
reinstall pinned versions from `requirements.txt`, and confirm with
`python check_env.py`.

### `cannot pickle '_thread.lock' object` on Ray Serve startup

This is a known incompatibility between `fastapi>=0.139.2` and Ray Serve's
`@serve.ingress` (ray-project/ray#64939) — that fastapi release added a
threading.Lock to its route caching that Ray's cloudpickle cannot serialize.
`requirements.txt` pins `fastapi==0.128.0` / `starlette==0.40.0` to avoid
this; if you see this error, your venv likely has an unpinned/newer fastapi.
Fix by reinstalling exactly:

```bash
pip install --no-user "fastapi==0.128.0" "starlette==0.40.0"
```

### Package conflict / `Can not perform a '--user' install`

Cloudera AI ML Runtime images ship `/etc/pip.conf` with `install.user = true`,
which pip config files take precedence over the `PIP_USER` env var. `setup.sh`
already passes `--no-user` explicitly to work around this; if you install
packages manually, always add `--no-user` too:

```bash
pip install --no-user <package>
```

The Application must use `launch_cai.py`. That launcher runs Python from
`.venv-ray-l4`, not the runtime's global packages.
