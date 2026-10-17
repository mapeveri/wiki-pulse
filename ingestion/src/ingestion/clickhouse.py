"""Thin helpers around the ClickHouse client."""

from __future__ import annotations

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from .config import ClickHouseConfig


def get_client(config: ClickHouseConfig) -> Client:
    """Create a ClickHouse client using the HTTP interface."""
    return clickhouse_connect.get_client(
        host=config.host,
        port=config.port,
        username=config.user,
        password=config.password,
        database=config.database,
    )
