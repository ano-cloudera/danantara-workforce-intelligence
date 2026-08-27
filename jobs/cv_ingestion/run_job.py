#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jobs.cv_ingestion.adapters import (  # noqa: E402
    GeminiExtractor,
    ObservabilityAdapter,
    QdrantAdapter,
    build_storage_adapter,
)
from jobs.cv_ingestion.config import JobSettings  # noqa: E402
from jobs.cv_ingestion.impala_repository import ImpalaRepository  # noqa: E402
from jobs.cv_ingestion.pipeline import CvIngestionPipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest new S3 CVs into Iceberg and Qdrant")
    parser.add_argument("--dry-run", action="store_true", help="extract without writing data")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = JobSettings.from_env()
    pipeline = CvIngestionPipeline(
        settings,
        build_storage_adapter(settings),
        GeminiExtractor(settings),
        ImpalaRepository(settings),
        QdrantAdapter(settings),
        ObservabilityAdapter(settings),
    )
    result = pipeline.run(dry_run=args.dry_run)
    print(
        "CV ingestion result: "
        f"discovered={result.discovered} processed={result.processed} "
        f"skipped={result.skipped} failed={result.failed}"
    )
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
