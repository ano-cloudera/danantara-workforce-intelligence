#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jobs.policy_ingestion.config import PolicyJobSettings  # noqa: E402
from jobs.policy_ingestion.impala_repository import PolicyImpalaRepository  # noqa: E402


def main() -> None:
    settings = PolicyJobSettings.from_env()
    ddl = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
    replacements = {
        "danantara.policy_documents": settings.policy_document_table,
        "danantara.policy_ingestion_audit": settings.policy_audit_table,
        "danantara.v_policy_documents_api": os.getenv(
            "IMPALA_POLICY_DOCUMENT_TABLE", "danantara.v_policy_documents_api"
        ),
    }
    for default, configured in replacements.items():
        ddl = ddl.replace(default, configured)
    PolicyImpalaRepository(settings).execute_ddl(ddl)
    print("Iceberg policy ingestion schema is ready")


if __name__ == "__main__":
    main()
