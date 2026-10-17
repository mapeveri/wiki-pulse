"""Runtime configuration, loaded from environment variables / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ClickHouseConfig:
    host: str = "localhost"
    port: int = 8123
    user: str = "default"
    password: str = ""
    database: str = "raw"

    @classmethod
    def from_env(cls) -> ClickHouseConfig:
        return cls(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            user=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            database=os.getenv("CLICKHOUSE_DB", "raw"),
        )


@dataclass(frozen=True)
class KafkaConfig:
    bootstrap_servers: str = "localhost:9092"
    consumer_group: str = "wikipulse-sink"

    @classmethod
    def from_env(cls) -> KafkaConfig:
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "wikipulse-sink"),
        )


@dataclass(frozen=True)
class Settings:
    clickhouse: ClickHouseConfig
    kafka: KafkaConfig
    wikimedia_user_agent: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            clickhouse=ClickHouseConfig.from_env(),
            kafka=KafkaConfig.from_env(),
            wikimedia_user_agent=os.getenv(
                "WIKIMEDIA_USER_AGENT",
                "seo-marketing-analytics-platform/0.1 (https://github.com/your-user/seo-marketing-analytics-platform)",
            ),
        )
