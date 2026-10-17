"""ClickHouse client wiring for the API."""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from .config import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


_local = threading.local()


def get_client() -> Client:
    """Return a ClickHouse client bound to the current thread.

    FastAPI runs synchronous endpoints in a thread pool and a clickhouse-connect
    session cannot run concurrent queries, so each worker thread gets its own
    client instead of sharing a single global one.
    """
    client = getattr(_local, "client", None)
    if client is None:
        settings = get_settings()
        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_db,
        )
        _local.client = client
    return client


def query(sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run a query and return the rows as a list of dicts."""
    result = get_client().query(sql, parameters=parameters or {})
    return list(result.named_results())
