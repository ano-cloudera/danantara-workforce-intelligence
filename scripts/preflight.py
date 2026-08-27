#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.cai_runtime import resolve_app_port  # noqa: E402

required = [
    "apps/frontend/run_cai.py",
    "apps/backend/run_cai.py",
    "apps/qdrant/run_cai.py",
    "apps/observability/run_cai.py",
    "jobs/cv_ingestion/run_cai_job.py",
    "jobs/cv_ingestion/schema.sql",
    "jobs/cv_ingestion/requirements.txt",
    "skills/delivery-method-selector/SKILL.md",
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
qdrant_runtime_vars = (
    "QDRANT_TIMEOUT_SECONDS",
    "QDRANT_CHECK_COMPATIBILITY",
    "QDRANT_TRUST_ENV",
)
missing_qdrant_runtime_vars = [
    name for name in qdrant_runtime_vars if f"{name}=" not in env_example
]
inter_app_url_vars = (
    "BACKEND_BASE_URL",
    "QDRANT_BASE_URL",
    "OBSERVABILITY_BASE_URL",
)
missing_inter_app_urls = [name for name in inter_app_url_vars if f"{name}=" not in env_example]
cv_job_vars = (
    "S3_CV_INPUT_URI",
    "S3_CV_PROCESSED_URI",
    "S3_CV_FAILED_URI",
    "ICEBERG_CANDIDATE_MASTER_TABLE",
    "ICEBERG_CANDIDATE_SKILLS_TABLE",
    "ICEBERG_CANDIDATE_EXPERIENCE_TABLE",
    "ICEBERG_INGESTION_AUDIT_TABLE",
)
missing_cv_job_vars = [name for name in cv_job_vars if f"{name}=" not in env_example]
launchers = [
    ROOT / "apps/frontend/run_cai.py",
    ROOT / "apps/backend/run_cai.py",
    ROOT / "apps/qdrant/run_cai.py",
    ROOT / "apps/observability/run_cai.py",
]
launcher_errors = []
for launcher in launchers:
    source = launcher.read_text()
    if "resolve_app_port" not in source or "resolve_bind_host" not in source:
        launcher_errors.append(f"{launcher.relative_to(ROOT)} does not use shared CAI resolution")
    if 'globals().get("__file__")' not in source or "CDSW_PROJECT_DIR" not in source:
        launcher_errors.append(
            f"{launcher.relative_to(ROOT)} cannot resolve paths in CAI cell execution"
        )
    if "parse_known_args" not in source:
        launcher_errors.append(
            f"{launcher.relative_to(ROOT)} cannot tolerate CAI interpreter arguments"
        )
    if "os.execv" in source:
        launcher_errors.append(
            f"{launcher.relative_to(ROOT)} replaces the CAI Python engine with os.execv"
        )
    if "CML_APP_PORT" in source:
        launcher_errors.append(f"{launcher.relative_to(ROOT)} still uses CML_APP_PORT")
    hardcoded_bindings = ("--port 8000", "--port 8080", "--port 8100", "--port 6333")
    if any(binding in source for binding in hardcoded_bindings):
        launcher_errors.append(f"{launcher.relative_to(ROOT)} hardcodes an exposed port")
    if launcher.parent.name != "qdrant" and (
        'pip_env.pop("PIP_USER", None)' not in source
        or '"--no-user"' not in source
        or '"--isolated"' not in source
    ):
        launcher_errors.append(
            f"{launcher.relative_to(ROOT)} does not neutralize CAI pip user-install mode"
        )
port_precedence_ok = (
    resolve_app_port(7000, {"CDSW_APP_PORT": "12001", "PORT": "12002"}) == 12001
    and resolve_app_port(7000, {"PORT": "12002"}) == 12002
    and resolve_app_port(7000, {}) == 7000
)
print("Danantara Workforce Intelligence preflight")
print("Repository:", ROOT)
print("Required files:", "OK" if not missing else "MISSING " + ",".join(missing))
print(
    "Qdrant workload collections:",
    "OK" if not missing_collection_vars else "MISSING " + ",".join(missing_collection_vars),
)
print(
    "Qdrant runtime configuration:",
    "OK"
    if not missing_qdrant_runtime_vars
    else "MISSING " + ",".join(missing_qdrant_runtime_vars),
)
print(
    "Inter-application URLs:",
    "OK" if not missing_inter_app_urls else "MISSING " + ",".join(missing_inter_app_urls),
)
print(
    "CAI CV ingestion Job configuration:",
    "OK" if not missing_cv_job_vars else "MISSING " + ",".join(missing_cv_job_vars),
)
print("CAI port precedence:", "OK" if port_precedence_ok else "FAILED")
print("CAI launcher port policy:", "OK" if not launcher_errors else "; ".join(launcher_errors))
print(
    "Gemini key in current environment:",
    "SET" if os.getenv("GEMINI_API_KEY") else "NOT SET (expected before runtime)",
)
print("Python:", sys.version.split()[0])
if (
    missing
    or missing_collection_vars
    or missing_qdrant_runtime_vars
    or missing_inter_app_urls
    or missing_cv_job_vars
    or not port_precedence_ok
    or launcher_errors
):
    raise SystemExit(1)
print("Preflight passed. Environment connectivity still requires target CAI validation.")
