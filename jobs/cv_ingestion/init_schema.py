#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jobs.cv_ingestion.config import JobSettings  # noqa: E402
from jobs.cv_ingestion.impala_repository import ImpalaRepository  # noqa: E402


def main() -> None:
    settings = JobSettings.from_env()
    ddl = (Path(__file__).resolve().parent / "schema.sql").read_text()
    replacements = {
        "danantara.candidate_master": settings.candidate_master_table,
        "danantara.candidate_skills": settings.candidate_skills_table,
        "danantara.candidate_experience": settings.candidate_experience_table,
        "danantara.cv_ingestion_audit": settings.ingestion_audit_table,
        "danantara.v_candidates_api": os.getenv(
            "IMPALA_CANDIDATE_TABLE", "danantara.v_candidates_api"
        ),
    }
    for default, configured in replacements.items():
        ddl = ddl.replace(default, configured)
    ImpalaRepository(settings).execute_ddl(ddl)
    print("Iceberg candidate ingestion schema is ready")


if __name__ == "__main__":
    main()
