#!/usr/bin/env python3
"""Create the configured shared-Qdrant collections when they are absent."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services.qdrant_service import QdrantService  # noqa: E402


def main() -> None:
    settings = get_settings()
    qdrant = QdrantService(settings, gemini=None)
    if not qdrant.client:
        raise SystemExit("Qdrant is disabled or the client could not be initialized")

    results = qdrant.ensure_required_collections()
    for name, created in results.items():
        print(f"{name}: {'created' if created else 'already exists'}")


if __name__ == "__main__":
    main()
