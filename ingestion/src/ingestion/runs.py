"""Track ingestion runs in raw.ingestion_runs for observability."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from clickhouse_connect.driver.client import Client


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class RunTracker:
    """Context manager that records a single ingestion run.

    Usage:
        with RunTracker(client, "wikimedia.pageviews") as run:
            rows = load(...)
            run.rows_loaded = len(rows)
    """

    client: Client
    source: str
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    started_at: datetime = field(default_factory=_now)
    rows_loaded: int = 0
    status: str = "running"
    error: str = ""

    def __enter__(self) -> "RunTracker":
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        if exc_type is not None:
            self.status = "failed"
            self.error = str(exc)
        else:
            self.status = "success"
        self._persist()
        return False

    def _persist(self) -> None:
        self.client.insert(
            "raw.ingestion_runs",
            [
                [
                    self.run_id,
                    self.source,
                    self.started_at,
                    _now(),
                    self.status,
                    self.rows_loaded,
                    self.error,
                ]
            ],
            column_names=[
                "run_id",
                "source",
                "started_at",
                "finished_at",
                "status",
                "rows_loaded",
                "error",
            ],
        )
