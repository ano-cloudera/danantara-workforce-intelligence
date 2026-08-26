#!/usr/bin/env python3
import os
import socket
import time
import uuid
from pathlib import Path
from typing import List, Optional

import ray
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from huggingface_hub import snapshot_download
from pydantic import BaseModel, Field
from ray import serve


MODEL_ID = os.getenv("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "./models/qwen2.5-0.5b-instruct")).resolve()
NUM_REPLICAS = int(os.getenv("NUM_REPLICAS", "2"))
GPU_PER_REPLICA = float(os.getenv("RAY_GPU_PER_REPLICA", "0.5"))
GPU_MEMORY_UTILIZATION = float(os.getenv("VLLM_GPU_MEMORY_UTILIZATION", "0.30"))
MAX_MODEL_LEN = int(os.getenv("MAX_MODEL_LEN", "512"))
MAX_NUM_SEQS = int(os.getenv("MAX_NUM_SEQS", "1"))
DTYPE = os.getenv("DTYPE", "float16")
APP_PORT = int(os.getenv("CDSW_APP_PORT", "8080"))
ALLOW_CRASH_TEST = os.getenv("ALLOW_CRASH_TEST", "false").lower() == "true"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, gt=0.0, le=1.0)
    max_tokens: int = Field(default=128, ge=1, le=512)


def prepare_model() -> str:
    if (MODEL_DIR / "config.json").exists():
        print(f"Using existing model: {MODEL_DIR}", flush=True)
        return str(MODEL_DIR)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_ID} to {MODEL_DIR}", flush=True)
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=str(MODEL_DIR),
        token=os.getenv("HF_TOKEN") or None,
    )
    return str(MODEL_DIR)


api = FastAPI(title="Ray + vLLM on Cloudera AI", version="1.0")


PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ray + vLLM L4 PoC</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 920px; margin: 36px auto; padding: 0 20px; color: #172033; }
    h1 { margin-bottom: 4px; } .muted { color: #667085; }
    textarea { width: 100%; height: 90px; padding: 12px; box-sizing: border-box; }
    button { margin: 10px 8px 10px 0; padding: 10px 16px; cursor: pointer; }
    pre { background: #101828; color: #e6edf3; padding: 16px; overflow: auto; min-height: 120px; }
    .pill { display: inline-block; padding: 5px 9px; margin-right: 6px; background: #eef4ff; border-radius: 12px; }
  </style>
</head>
<body>
  <h1>Ray + vLLM on one NVIDIA L4</h1>
  <p class="muted">Two Ray Serve replicas logically share one physical GPU.</p>
  <p><span class="pill">2 replicas</span><span class="pill">0.5 Ray GPU each</span><span class="pill">30% vLLM memory each</span></p>
  <textarea id="prompt">Explain Ray soft GPU sharing in one short sentence.</textarea><br>
  <button onclick="ask()">Send one request</button>
  <button onclick="routeTest()">Send 8 concurrent requests</button>
  <button onclick="health()">Health</button>
  <pre id="out">Ready.</pre>
  <script>
    const out = document.getElementById('out');
    async function request(i=0) {
      const body = {model:'ray-l4-poc', messages:[{role:'user', content:document.getElementById('prompt').value + ' Request ' + i}], temperature:0.1, max_tokens:80};
      const r = await fetch('./v1/chat/completions', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      const j = await r.json();
      if (!r.ok) throw new Error(JSON.stringify(j));
      return {replica:j.x_ray, answer:j.choices[0].message.content};
    }
    async function ask() { out.textContent='Running...'; try { out.textContent=JSON.stringify(await request(), null, 2); } catch(e) { out.textContent=e; } }
    async function routeTest() { out.textContent='Running 8 requests...'; try { const r=await Promise.all(Array.from({length:8},(_,i)=>request(i))); out.textContent=JSON.stringify(r, null, 2); } catch(e) { out.textContent=e; } }
    async function health() { const r=await fetch('./health'); out.textContent=JSON.stringify(await r.json(), null, 2); }
  </script>
</body>
</html>"""


@serve.deployment
@serve.ingress(api)
class VLLMReplica:
    def __init__(self, model_path: str):
        from vllm import LLM

        self.started_at = time.time()
        self.replica_id = f"{socket.gethostname()}:{os.getpid()}"
        self.visible_gpu = os.getenv("CUDA_VISIBLE_DEVICES", "not-set")
        runtime_context = ray.get_runtime_context()
        self.ray_assigned_resources = runtime_context.get_assigned_resources()
        self.ray_accelerator_ids = runtime_context.get_accelerator_ids()
        print(
            f"Starting replica {self.replica_id}; "
            f"CUDA_VISIBLE_DEVICES={self.visible_gpu}; "
            f"assigned_resources={self.ray_assigned_resources}; "
            f"accelerator_ids={self.ray_accelerator_ids}",
            flush=True,
        )
        self.llm = LLM(
            model=model_path,
            dtype=DTYPE,
            tensor_parallel_size=1,
            max_model_len=MAX_MODEL_LEN,
            max_num_seqs=MAX_NUM_SEQS,
            gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
            enforce_eager=True,
            trust_remote_code=False,
        )

    @api.get("/", response_class=HTMLResponse)
    def root(self):
        return (
            PAGE.replace("2 replicas", f"{NUM_REPLICAS} replicas")
            .replace("0.5 Ray GPU each", f"{GPU_PER_REPLICA:g} Ray GPU each")
            .replace(
                "30% vLLM memory each",
                f"{GPU_MEMORY_UTILIZATION * 100:g}% vLLM memory each",
            )
        )

    @api.get("/health")
    def health(self):
        return {
            "status": "ok",
            "model": MODEL_ID,
            "replica_id": self.replica_id,
            "cuda_visible_devices": self.visible_gpu,
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "ray_gpu_per_replica": GPU_PER_REPLICA,
            "vllm_gpu_memory_utilization": GPU_MEMORY_UTILIZATION,
            "ray_assigned_resources": self.ray_assigned_resources,
            "ray_accelerator_ids": self.ray_accelerator_ids,
        }

    @api.post("/v1/chat/completions")
    def chat(self, request: ChatRequest):
        from vllm import SamplingParams

        messages = [message.model_dump() for message in request.messages]
        params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
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
            "model": request.model or MODEL_ID,
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
                "replica_id": self.replica_id,
                "cuda_visible_devices": self.visible_gpu,
                "latency_seconds": round(time.perf_counter() - started, 3),
                "ray_assigned_resources": self.ray_assigned_resources,
                "ray_accelerator_ids": self.ray_accelerator_ids,
            },
        }

    @api.post("/debug/crash")
    def crash(self):
        if not ALLOW_CRASH_TEST:
            raise HTTPException(status_code=403, detail="Set ALLOW_CRASH_TEST=true first")
        os._exit(137)

    def check_health(self):
        if self.llm is None:
            raise RuntimeError("vLLM engine is not initialized")


def validate_configuration():
    if NUM_REPLICAS < 1:
        raise ValueError("NUM_REPLICAS must be at least 1")
    if NUM_REPLICAS * GPU_PER_REPLICA > 1.0001:
        raise ValueError("This one-L4 PoC cannot reserve more than one Ray GPU in total")
    if NUM_REPLICAS * GPU_MEMORY_UTILIZATION > 0.90:
        raise ValueError("Keep combined VLLM_GPU_MEMORY_UTILIZATION at or below 0.90")


def main():
    validate_configuration()
    model_path = prepare_model()
    ray.init(
        namespace="cai-ray-l4-poc",
        include_dashboard=True,
        dashboard_host="127.0.0.1",
        ignore_reinit_error=True,
    )
    print("Ray cluster resources:", ray.cluster_resources(), flush=True)
    if ray.cluster_resources().get("GPU", 0) < 1:
        raise RuntimeError("Ray cannot see an NVIDIA GPU. Check the CAI Application GPU resource.")

    serve.start(http_options={"host": "127.0.0.1", "port": APP_PORT})
    deployment = VLLMReplica.options(
        num_replicas=NUM_REPLICAS,
        ray_actor_options={"num_cpus": 1, "num_gpus": GPU_PER_REPLICA},
        max_ongoing_requests=1,
        health_check_period_s=20,
        health_check_timeout_s=120,
        graceful_shutdown_timeout_s=30,
    ).bind(model_path)
    serve.run(deployment, name="ray-l4-poc", route_prefix="/")
    print(f"Ready on 127.0.0.1:{APP_PORT}", flush=True)

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
