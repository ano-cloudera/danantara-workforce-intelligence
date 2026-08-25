#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "apps/frontend/run_cai.py",
    "apps/backend/run_cai.py",
    "apps/qdrant/run_cai.py",
    "apps/observability/run_cai.py",
    "data/nifi-demo",
    "data/workforce-app",
    "PROJECT_STATE.md",
    "BRD.md",
    "PRD.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
env_example = (ROOT / ".env.example").read_text()
qdrant_collection_vars = (
    "QDRANT_NIFI_COLLECTION",
    "QDRANT_CANDIDATE_COLLECTION",
    "QDRANT_POLICY_COLLECTION",
)
missing_collection_vars = [name for name in qdrant_collection_vars if f"{name}=" not in env_example]
print("Danantara Workforce Intelligence preflight")
print("Repository:", ROOT)
print("Required files:", "OK" if not missing else "MISSING " + ",".join(missing))
print(
    "Qdrant workload collections:",
    "OK" if not missing_collection_vars else "MISSING " + ",".join(missing_collection_vars),
)
print(
    "Gemini key in current environment:",
    "SET" if os.getenv("GEMINI_API_KEY") else "NOT SET (expected before runtime)",
)
print("Python:", sys.version.split()[0])
if missing or missing_collection_vars:
    raise SystemExit(1)
print("Preflight passed. Environment connectivity still requires target CAI validation.")
