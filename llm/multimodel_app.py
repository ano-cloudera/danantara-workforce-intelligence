#!/usr/bin/env python3
import os
import site
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import List, Literal, Optional, Union


PROJECT_DIR = Path("/home/cdsw/ray-l4-cai-poc")
VENV_DIR = PROJECT_DIR / ".venv-ray-l4"
SCRIPT_PATH = PROJECT_DIR / "multimodel_app.py"


def activate_project_environment():
    """Expose the project venv without replacing the CAI IPython engine."""
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = VENV_DIR / "lib" / python_version / "site-packages"
    venv_bin = VENV_DIR / "bin"

    if not site_packages.is_dir():
        raise SystemExit(f"Project site-packages not found: {site_packages}")

    site.addsitedir(str(site_packages))
    site_path = str(site_packages)
    while site_path in sys.path:
        sys.path.remove(site_path)
    sys.path.insert(0, site_path)

    os.environ["VIRTUAL_ENV"] = str(VENV_DIR)
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = (
        f"{site_packages}:{current_pythonpath}"
        if current_pythonpath
        else str(site_packages)
    )
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.chdir(PROJECT_DIR)
    print(f"Project environment activated: {site_packages}", flush=True)


activate_project_environment()

import ray
from fastapi import FastAPI
from huggingface_hub import snapshot_download
from pydantic import BaseModel, Field
from ray import serve


BASE_DIR = Path(os.getenv("MODEL_BASE_DIR", "/home/cdsw/ray-l4-cai-poc/models"))
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "Qwen/Qwen3-14B")
LLM_MODEL_DIR = Path(
    os.getenv("LLM_MODEL_DIR", str(BASE_DIR / "qwen3-14b"))
)
EMBED_MODEL_ID = os.getenv("EMBED_MODEL_ID", "BAAI/bge-m3")
EMBED_MODEL_DIR = Path(
    os.getenv("EMBED_MODEL_DIR", str(BASE_DIR / "bge-m3"))
)

# 4x A10G (24 GB each) target: 2 GPUs dedicated to the LLM via vLLM tensor
# parallelism, 2 GPUs dedicated to embedding replicas. These are whole-GPU
# allocations (not soft-shared fractional GPUs like the single-L4 PoC).
LLM_TENSOR_PARALLEL_SIZE = int(os.getenv("LLM_TENSOR_PARALLEL_SIZE", "2"))
LLM_GPU_MEMORY_UTILIZATION = float(
    os.getenv("LLM_GPU_MEMORY_UTILIZATION", "0.90")
)
EMBED_NUM_REPLICAS = int(os.getenv("EMBED_NUM_REPLICAS", "2"))
EMBED_GPU_PER_REPLICA = float(os.getenv("EMBED_GPU_PER_REPLICA", "1.0"))
MAX_MODEL_LEN = int(os.getenv("MAX_MODEL_LEN", "8192"))
MAX_NUM_SEQS = int(os.getenv("MAX_NUM_SEQS", "16"))
DTYPE = os.getenv("DTYPE", "bfloat16")
APP_PORT = int(os.getenv("CDSW_APP_PORT", "8080"))


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, gt=0.0, le=1.0)
    max_tokens: int = Field(default=128, ge=1, le=512)


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: Optional[str] = None
    input_type: Literal["query", "passage"] = "query"


def ensure_model(repo_id: str, model_dir: Path) -> str:
    model_dir = model_dir.resolve()
    has_config = (model_dir / "config.json").is_file()
    has_weights = any(
        (
            (model_dir / "model.safetensors").is_file(),
            (model_dir / "model.safetensors.index.json").is_file(),
            (model_dir / "pytorch_model.bin").is_file(),
            (model_dir / "pytorch_model.bin.index.json").is_file(),
        )
    )
    if has_config and has_weights:
        print(f"Using existing model: {model_dir}", flush=True)
        return str(model_dir)

    model_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {repo_id} to {model_dir}", flush=True)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(model_dir),
        token=os.getenv("HF_TOKEN") or None,
        ignore_patterns=[
            "onnx/*",
            "openvino/*",
            "*.yaml",
            "*.msgpack",
            "flax_model*",
            "tf_model*",
            "pytorch_model.bin",
        ],
        max_workers=1,
    )
    return str(model_dir)


def runtime_metadata() -> dict:
    context = ray.get_runtime_context()
    return {
        "replica_id": f"{socket.gethostname()}:{os.getpid()}",
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES", "not-set"),
        "ray_assigned_resources": context.get_assigned_resources(),
        "ray_accelerator_ids": context.get_accelerator_ids(),
    }


@serve.deployment
class LLMDeployment:
    def __init__(self, model_path: str):
        from vllm import LLM

        self.started_at = time.time()
        self.runtime = runtime_metadata()
        print(f"Starting LLM deployment: {self.runtime}", flush=True)
        # tensor_parallel_size>1 makes vLLM spawn its own Ray worker actors
        # internally (distributed_executor_backend="ray") to shard the model
        # across LLM_TENSOR_PARALLEL_SIZE whole GPUs reserved by this deployment.
        self.llm = LLM(
            model=model_path,
            dtype=DTYPE,
            tensor_parallel_size=LLM_TENSOR_PARALLEL_SIZE,
            distributed_executor_backend="ray" if LLM_TENSOR_PARALLEL_SIZE > 1 else None,
            max_model_len=MAX_MODEL_LEN,
            max_num_seqs=MAX_NUM_SEQS,
            gpu_memory_utilization=LLM_GPU_MEMORY_UTILIZATION,
            enforce_eager=False,
            trust_remote_code=False,
        )

    def health(self):
        return {
            "status": "ok",
            "deployment": "llm",
            "model": LLM_MODEL_ID,
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "gpu_memory_utilization": LLM_GPU_MEMORY_UTILIZATION,
            **self.runtime,
        }

    def chat(self, payload: dict):
        from vllm import SamplingParams

        messages = payload["messages"]
        params = SamplingParams(
            temperature=payload.get("temperature", 0.2),
            top_p=payload.get("top_p", 0.9),
            max_tokens=payload.get("max_tokens", 128),
        )
        started = time.perf_counter()
        outputs = self.llm.chat(messages, sampling_params=params, use_tqdm=False)
        result = outputs[0]
        completion = result.outputs[0]
        prompt_tokens = len(result.prompt_token_ids)
        completion_tokens = len(completion.token_ids)
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:16]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.get("model") or LLM_MODEL_ID,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": completion.text},
                    "finish_reason": completion.finish_reason or "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "x_ray": {
                **self.runtime,
                "latency_seconds": round(time.perf_counter() - started, 3),
            },
        }


@serve.deployment
class EmbeddingDeployment:
    def __init__(self, model_path: str):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.started_at = time.time()
        self.runtime = runtime_metadata()
        print(f"Starting embedding deployment: {self.runtime}", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path)
        self.model.eval()
        self.model.to("cuda")

    def health(self):
        return {
            "status": "ok",
            "deployment": "embedding",
            "model": EMBED_MODEL_ID,
            "uptime_seconds": round(time.time() - self.started_at, 1),
            **self.runtime,
        }

    def encode(self, texts: List[str]):
        # BGE-M3 dense embeddings use the [CLS] token, not e5-style mean
        # pooling, and do not need a "query:"/"passage:" prefix.
        started = time.perf_counter()

        encoded = self.tokenizer(
            texts,
            max_length=8192,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        encoded = {name: value.to("cuda") for name, value in encoded.items()}

        with self.torch.inference_mode():
            output = self.model(**encoded)
            embeddings = output.last_hidden_state[:, 0]
            embeddings = self.torch.nn.functional.normalize(embeddings, p=2, dim=1)

        vectors = embeddings.float().cpu().tolist()
        return {
            "vectors": vectors,
            "token_count": int(encoded["attention_mask"].sum().item()),
            "runtime": {
                **self.runtime,
                "latency_seconds": round(time.perf_counter() - started, 3),
            },
        }


api = FastAPI(title="Ray Multi-Model API on Cloudera AI", version="1.0")


@serve.deployment
@serve.ingress(api)
class APIIngress:
    def __init__(self, llm_handle, embedding_handle):
        self.llm = llm_handle
        self.embedding = embedding_handle

    @api.get("/")
    def root(self):
        return {
            "service": "Ray multi-model serving on Cloudera AI",
            "endpoints": {
                "health": "GET /health",
                "chat": "POST /v1/chat/completions",
                "embeddings": "POST /v1/embeddings",
            },
            "allocation": {
                "llm_model": LLM_MODEL_ID,
                "llm_tensor_parallel_size": LLM_TENSOR_PARALLEL_SIZE,
                "embedding_model": EMBED_MODEL_ID,
                "embedding_num_replicas": EMBED_NUM_REPLICAS,
                "embedding_gpu_per_replica": EMBED_GPU_PER_REPLICA,
                "total_gpus": LLM_TENSOR_PARALLEL_SIZE
                + EMBED_NUM_REPLICAS * EMBED_GPU_PER_REPLICA,
            },
        }

    @api.get("/health")
    async def health(self):
        llm_health, embedding_health = await self.llm.health.remote(), await self.embedding.health.remote()
        return {
            "status": "ok",
            "llm": llm_health,
            "embedding": embedding_health,
        }

    @api.post("/v1/chat/completions")
    async def chat(self, request: ChatRequest):
        payload = request.model_dump()
        payload["messages"] = [message.model_dump() for message in request.messages]
        return await self.llm.chat.remote(payload)

    @api.post("/v1/embeddings")
    async def embeddings(self, request: EmbeddingRequest):
        texts = [request.input] if isinstance(request.input, str) else request.input
        result = await self.embedding.encode.remote(texts)
        return {
            "object": "list",
            "data": [
                {"object": "embedding", "index": index, "embedding": vector}
                for index, vector in enumerate(result["vectors"])
            ],
            "model": request.model or EMBED_MODEL_ID,
            "usage": {
                "prompt_tokens": result["token_count"],
                "total_tokens": result["token_count"],
            },
            "x_ray": result["runtime"],
        }


def validate_configuration():
    total_gpu = LLM_TENSOR_PARALLEL_SIZE + EMBED_NUM_REPLICAS * EMBED_GPU_PER_REPLICA
    if LLM_TENSOR_PARALLEL_SIZE <= 0:
        raise ValueError("LLM_TENSOR_PARALLEL_SIZE must be greater than zero")
    if EMBED_NUM_REPLICAS <= 0 or EMBED_GPU_PER_REPLICA <= 0:
        raise ValueError("EMBED_NUM_REPLICAS and EMBED_GPU_PER_REPLICA must be greater than zero")
    if total_gpu > 4.0001:
        raise ValueError(f"Logical GPU allocation exceeds the 4 available GPUs: {total_gpu}")
    if not 0 < LLM_GPU_MEMORY_UTILIZATION < 0.95:
        raise ValueError("LLM_GPU_MEMORY_UTILIZATION must be between 0 and 0.95")


def main():
    validate_configuration()
    llm_path = ensure_model(LLM_MODEL_ID, LLM_MODEL_DIR)
    embedding_path = ensure_model(EMBED_MODEL_ID, EMBED_MODEL_DIR)

    ray.init(
        namespace="cai-ray-multimodel",
        include_dashboard=True,
        dashboard_host="127.0.0.1",
        ignore_reinit_error=True,
    )
    print("Ray cluster resources:", ray.cluster_resources(), flush=True)
    available_gpu = ray.cluster_resources().get("GPU", 0)
    required_gpu = LLM_TENSOR_PARALLEL_SIZE + EMBED_NUM_REPLICAS * EMBED_GPU_PER_REPLICA
    if available_gpu < required_gpu:
        raise RuntimeError(
            f"Ray sees {available_gpu} GPU(s) but {required_gpu} are required "
            "(LLM_TENSOR_PARALLEL_SIZE + EMBED_NUM_REPLICAS * EMBED_GPU_PER_REPLICA)"
        )

    serve.start(http_options={"host": "127.0.0.1", "port": APP_PORT})

    # vLLM manages its own Ray worker actors for tensor parallelism, so the
    # deployment actor itself only needs a driver CPU slot; the num_gpus
    # reservation here reserves the whole TP group up front on the cluster.
    llm = LLMDeployment.options(
        num_replicas=1,
        ray_actor_options={"num_cpus": 2, "num_gpus": LLM_TENSOR_PARALLEL_SIZE},
        health_check_period_s=20,
        health_check_timeout_s=180,
    ).bind(llm_path)

    embedding = EmbeddingDeployment.options(
        num_replicas=EMBED_NUM_REPLICAS,
        ray_actor_options={"num_cpus": 2, "num_gpus": EMBED_GPU_PER_REPLICA},
        health_check_period_s=20,
        health_check_timeout_s=120,
    ).bind(embedding_path)

    application = APIIngress.options(
        ray_actor_options={"num_cpus": 1}
    ).bind(llm, embedding)

    serve.run(application, name="ray-multimodel", route_prefix="/")
    print(f"Multi-model API ready on 127.0.0.1:{APP_PORT}", flush=True)

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
