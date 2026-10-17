"""ClickHouse client wiring for the API."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from .config import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache
def get_client() -> Client:
    settings = get_settings()
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_db,
    )


def query(sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run a query and return the rows as a list of dicts."""
    result = get_client().query(sql, parameters=parameters or {})
    return list(result.named_results())
