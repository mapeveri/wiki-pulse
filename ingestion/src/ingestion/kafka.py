"""Kafka / Redpanda helpers: topic names and client factories."""

from __future__ import annotations

from confluent_kafka import Consumer, Producer

from .config import KafkaConfig

# Topics
PAGEVIEWS_TOPIC = "pageviews.raw"
ARTICLES_TOPIC = "articles.raw"
DLQ_SUFFIX = ".dlq"


def get_producer(config: KafkaConfig) -> Producer:
    """Idempotent producer: no duplicates on internal retries."""
    return Producer(
        {
            "bootstrap.servers": config.bootstrap_servers,
            "enable.idempotence": True,
            "acks": "all",
            "client.id": "wikipulse-producer",
        }
    )


def get_consumer(config: KafkaConfig, *, auto_reset: str = "earliest") -> Consumer:
    """Consumer with manual offset commits (commit only after persistence)."""
    return Consumer(
        {
            "bootstrap.servers": config.bootstrap_servers,
            "group.id": config.consumer_group,
            "auto.offset.reset": auto_reset,
            "enable.auto.commit": False,
            "enable.partition.eof": False,
            "client.id": "wikipulse-sink",
        }
    )
