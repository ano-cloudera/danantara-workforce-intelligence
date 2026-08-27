#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jobs.policy_ingestion.adapters import (  # noqa: E402
    GeminiEmbedder,
    ObservabilityAdapter,
    PolicyExtractor,
    QdrantPolicyAdapter,
    build_storage_adapter,
)
from jobs.policy_ingestion.config import PolicyJobSettings  # noqa: E402
from jobs.policy_ingestion.guardrails import PolicyIngestionGuardrails  # noqa: E402
from jobs.policy_ingestion.impala_repository import PolicyImpalaRepository  # noqa: E402
from jobs.policy_ingestion.pipeline import PolicyIngestionPipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest governed policies into Iceberg and Qdrant")
    parser.add_argument("--dry-run", action="store_true", help="validate without external writes")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = PolicyJobSettings.from_env()
    pipeline = PolicyIngestionPipeline(
        settings,
        build_storage_adapter(settings),
        PolicyExtractor(),
        PolicyIngestionGuardrails(
            settings.max_file_bytes, settings.max_chunks, settings.gemini_embed_dim
        ),
        PolicyImpalaRepository(settings),
        GeminiEmbedder(settings),
        QdrantPolicyAdapter(settings),
        ObservabilityAdapter(settings),
    )
    result = pipeline.run(dry_run=args.dry_run)
    print(
        "Policy ingestion result: "
        f"discovered={result.discovered} processed={result.processed} "
        f"review_required={result.review_required} skipped={result.skipped} "
        f"failed={result.failed}"
    )
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
