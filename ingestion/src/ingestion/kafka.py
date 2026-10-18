"""Kafka / Redpanda helpers: topic names and client factories."""

from __future__ import annotations

from confluent_kafka import Consumer, Producer

from .config import KafkaConfig

# Topics
PAGEVIEWS_TOPIC = "pageviews.raw"
ARTICLES_TOPIC = "articles.raw"
DLQ_SUFFIX = ".dlq"


def get_producer(
    config: KafkaConfig,
    *,
    client_id: str = "wikipulse-producer",
    compression: str = "snappy",
    linger_ms: int = 20,
) -> Producer:
    """Idempotent producer: no duplicates on internal retries.

    ``enable.idempotence`` forces ``acks=all`` and bounded in-flight requests, so
    a retried batch cannot be reordered or duplicated within the producer
    session. Compression keeps wire/broker usage down; a small ``linger.ms``
    gives batches a chance to form without adding much latency.
    """
    return Producer(
        {
            "bootstrap.servers": config.bootstrap_servers,
            "enable.idempotence": True,
            "acks": "all",
            "compression.type": compression,
            "linger.ms": linger_ms,
            "client.id": client_id,
        }
    )


def get_consumer(
    config: KafkaConfig,
    *,
    auto_reset: str = "earliest",
    max_poll_interval_ms: int = 300_000,
    max_poll_records: int = 500,
    fetch_max_bytes: int = 52_428_800,
    max_partition_fetch_bytes: int = 1_048_576,
    client_id: str = "wikipulse-sink",
) -> Consumer:
    """Consumer with manual offset commits (commit only after persistence) and
    bounds that keep each poll cycle well within ``max.poll.interval.ms``.

    Kafka evicts a consumer from the group (rebalance) if it does not call
    ``poll`` within ``max.poll.interval.ms``. Capping ``max.poll.records`` and the
    fetch sizes guarantees every poll cycle yields a bounded amount of work that
    the sink can persist comfortably in time.
    """
    return Consumer(
        {
            "bootstrap.servers": config.bootstrap_servers,
            "group.id": config.consumer_group,
            "auto.offset.reset": auto_reset,
            "enable.auto.commit": False,
            "enable.partition.eof": False,
            "max.poll.interval.ms": max_poll_interval_ms,
            "max.poll.records": max_poll_records,
            "fetch.max.bytes": fetch_max_bytes,
            "max.partition.fetch.bytes": max_partition_fetch_bytes,
            "client.id": client_id,
        }
    )
