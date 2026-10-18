"""Inspect and replay the dead-letter queues.

The sink routes malformed records (and batches that fail to insert after
retries) to ``<topic>.dlq``. This CLI reads those messages so they can be
reviewed or re-published to their original topic.

Examples:
    wikipulse-dlq --topic pageviews.raw.dlq --mode inspect
    wikipulse-dlq --topic pageviews.raw.dlq --mode replay --commit
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Iterator

from confluent_kafka import Consumer, KafkaError, KafkaException, Message, Producer

from .config import Settings
from .kafka import get_producer


def _build_consumer(settings: Settings, group: str) -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": settings.kafka.bootstrap_servers,
            "group.id": group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "enable.partition.eof": False,
            "client.id": "wikipulse-dlq",
        }
    )


def _drain(consumer: Consumer, limit: int, idle_timeout: float) -> Iterator[Message]:
    """Yield messages until the limit is reached or the topic goes idle."""
    received = 0
    idle_since = time.monotonic()
    while received < limit:
        messages = consumer.consume(num_messages=100, timeout=1.0)
        if not messages:
            if time.monotonic() - idle_since >= idle_timeout:
                break
            continue
        idle_since = time.monotonic()
        for message in messages:
            if message.error():
                print(f"consume error: {message.error()}", file=sys.stderr)
                continue
            received += 1
            yield message


def _inspect(messages: Iterator[Message]) -> None:
    count = 0
    for message in messages:
        payload = json.loads(message.value())
        count += 1
        print(
            f"[{count}] {payload.get('topic')} "
            f"partition={payload.get('partition')} offset={payload.get('offset')}"
        )
        print(f"    error: {payload.get('error')}")
        print(f"    value: {payload.get('value')}")
    print(f"{count} dead-letter message(s)")


def _replay(messages: Iterator[Message], settings: Settings) -> int:
    producer: Producer = get_producer(settings.kafka, client_id="wikipulse-dlq-replay")
    delivered = 0

    def on_delivery(error: KafkaError | None, _message: Message) -> None:
        nonlocal delivered
        if error is None:
            delivered += 1
        else:
            print(f"replay delivery failed: {error}", file=sys.stderr)

    replayed = 0
    for message in messages:
        payload = json.loads(message.value())
        target = payload.get("topic")
        value = payload.get("value")
        if not target or value is None:
            print(
                f"skipping malformed DLQ record at offset {message.offset()}",
                file=sys.stderr,
            )
            continue
        producer.produce(target, value=value.encode(), callback=on_delivery)
        producer.poll(0)
        replayed += 1
    producer.flush()
    print(f"replayed {delivered}/{replayed} message(s)")
    return replayed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wikipulse-dlq",
        description="Inspect or replay messages parked in a dead-letter queue.",
    )
    parser.add_argument("--topic", required=True, help="DLQ topic, e.g. pageviews.raw.dlq")
    parser.add_argument("--mode", choices=["inspect", "replay"], default="inspect")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--group", default="wikipulse-dlq")
    parser.add_argument("--idle-timeout", type=float, default=5.0)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="commit DLQ offsets after a replay (otherwise messages stay for review)",
    )
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    consumer = _build_consumer(settings, args.group)
    consumer.subscribe([args.topic])
    try:
        messages = _drain(consumer, args.limit, args.idle_timeout)
        if args.mode == "replay":
            replayed = _replay(messages, settings)
            if args.commit and replayed:
                consumer.commit(asynchronous=False)
        else:
            _inspect(messages)
    except KafkaException as exc:
        print(f"Kafka error: {exc}", file=sys.stderr)
        return 1
    finally:
        consumer.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
