#!/usr/bin/env python3
"""Create the Impala/Iceberg table and view backing dashboard recruitment-pipeline metrics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services.data_gateway import DataGateway  # noqa: E402


def main() -> None:
    settings = get_settings()
    if not settings.impala_host:
        raise SystemExit("IMPALA_HOST is required to initialize the dashboard schema")
    ddl = (Path(__file__).resolve().parent / "dashboard_schema.sql").read_text(encoding="utf-8")
    gateway = DataGateway(settings)
    with gateway._connect() as connection:  # noqa: SLF001
        cursor = connection.cursor()
        for statement in (part.strip() for part in ddl.split(";") if part.strip()):
            cursor.execute(statement)
    print("Dashboard recruitment-pipeline schema is ready")


if __name__ == "__main__":
    main()
