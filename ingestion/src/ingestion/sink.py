"""Kafka -> ClickHouse sink.

The only component that writes to ClickHouse. It consumes events from Redpanda,
validates and batches them, inserts into the raw tables and only then commits
offsets.

Guarantees demonstrated here:

* **at-least-once**: offsets are committed only after a successful insert, so a
  crash between insert and commit reprocesses the batch instead of losing it;
* **idempotency in the warehouse**: raw tables are ``ReplacingMergeTree`` keyed by
  the logical row, so reprocessing a batch does not create duplicates;
* **backpressure**: partitions are paused while a batch is being persisted, so
  the sink never accumulates unbounded work in memory;
* **dead-letter queue**: records that cannot be parsed, or batches that fail to
  insert after retries, are sent to ``<topic>.dlq``.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import uuid4

from clickhouse_connect.driver.client import Client
from confluent_kafka import Consumer, KafkaError, Message, Producer

from .clickhouse import get_client
from .config import Settings
from .kafka import (
    ARTICLES_TOPIC,
    DLQ_SUFFIX,
    PAGEVIEWS_TOPIC,
    get_consumer,
    get_producer,
)

RowBuilder = Callable[[dict], list]


def _pageview_row(event: dict) -> list:
    return [
        event["project"],
        event["article"],
        event["access"],
        event["agent"],
        event["granularity"],
        date.fromisoformat(event["ts"]),
        int(event["views"]),
    ]


def _article_row(event: dict) -> list:
    return [
        event["project"],
        event["article"],
        event["url"],
        event["title"],
        int(event["word_count"]),
        int(event["section_count"]),
        int(event["internal_links"]),
        int(event["external_links"]),
        datetime.strptime(event["crawled_at"], "%Y-%m-%d %H:%M:%S"),
    ]


@dataclass(frozen=True)
class Handler:
    table: str
    columns: list[str]
    build_row: RowBuilder


HANDLERS: dict[str, Handler] = {
    PAGEVIEWS_TOPIC: Handler(
        table="raw.pageviews",
        columns=["project", "article", "access", "agent", "granularity", "ts", "views"],
        build_row=_pageview_row,
    ),
    ARTICLES_TOPIC: Handler(
        table="raw.articles",
        columns=[
            "project",
            "article",
            "url",
            "title",
            "word_count",
            "section_count",
            "internal_links",
            "external_links",
            "crawled_at",
        ],
        build_row=_article_row,
    ),
}

RUN_COLUMNS = [
    "run_id",
    "source",
    "started_at",
    "finished_at",
    "status",
    "rows_loaded",
    "error",
]


class Sink:
    def __init__(
        self,
        settings: Settings,
        *,
        batch_size: int = 1000,
        flush_interval: float = 5.0,
        max_retries: int = 3,
        high_watermark: int = 5000,
    ) -> None:
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        self.high_watermark = high_watermark

        self.consumer: Consumer = get_consumer(settings.kafka)
        self.client: Client = get_client(settings.clickhouse)
        self.dlq: Producer = get_producer(settings.kafka)

        # topic -> list of (row, message) so a failed batch can be sent to the DLQ.
        self.buffers: dict[str, list[tuple[list, Message]]] = {
            topic: [] for topic in HANDLERS
        }
        self._last_flush = time.monotonic()
        self._running = True

    # -- lifecycle ---------------------------------------------------------

    def stop(self, *_args: object) -> None:
        self._running = False

    def run(self) -> None:
        self.consumer.subscribe(list(HANDLERS))
        print(f"Sink subscribed to: {', '.join(HANDLERS)}")
        try:
            while self._running:
                messages = self.consumer.consume(num_messages=500, timeout=1.0)
                for message in messages:
                    if message.error():
                        if message.error().code() != KafkaError._PARTITION_EOF:
                            print(f"consume error: {message.error()}", file=sys.stderr)
                        continue
                    self._handle_message(message)
                if self._should_flush():
                    self._flush_all()
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        self._flush_all()
        self.consumer.close()
        self.dlq.flush()
        print("Sink stopped")

    # -- consuming ---------------------------------------------------------

    def _handle_message(self, message: Message) -> None:
        topic = message.topic()
        handler = HANDLERS.get(topic)
        if handler is None:
            return
        try:
            event = json.loads(message.value())
            row = handler.build_row(event)
        except (ValueError, KeyError, TypeError) as exc:
            self._send_to_dlq(message, exc)
            return
        self.buffers[topic].append((row, message))

    def _buffered(self) -> int:
        return sum(len(buffer) for buffer in self.buffers.values())

    def _should_flush(self) -> bool:
        if any(len(buffer) >= self.batch_size for buffer in self.buffers.values()):
            return True
        if self._buffered() >= self.high_watermark:
            return True
        return self._buffered() > 0 and (
            time.monotonic() - self._last_flush >= self.flush_interval
        )

    # -- persistence -------------------------------------------------------

    def _flush_all(self) -> None:
        # Backpressure: stop pulling from Kafka while we persist.
        self._pause()
        flushed = False
        try:
            for topic, buffer in self.buffers.items():
                if buffer:
                    self._flush_topic(topic, buffer)
                    flushed = True
            # Commit only when we actually persisted a batch: committing with no
            # stored offsets raises _NO_OFFSET (e.g. on an idle shutdown).
            if flushed:
                self.consumer.commit(asynchronous=False)
                self._last_flush = time.monotonic()
        finally:
            self._resume()

    def _flush_topic(self, topic: str, buffer: list[tuple[list, Message]]) -> None:
        handler = HANDLERS[topic]
        rows = [row for row, _message in buffer]

        for attempt in range(1, self.max_retries + 1):
            try:
                self.client.insert(handler.table, rows, column_names=handler.columns)
            except Exception as exc:  # noqa: BLE001 - sink must survive any insert error
                if attempt == self.max_retries:
                    print(
                        f"insert failed permanently for {topic}: {exc}", file=sys.stderr
                    )
                    for _row, message in buffer:
                        self._send_to_dlq(message, exc)
                    self._record_run(topic, 0, "failed", str(exc))
                else:
                    time.sleep(2**attempt)
                    continue
            else:
                print(f"  {topic}: inserted {len(rows)} rows")
                self._record_run(topic, len(rows), "success", "")
            break

        self.buffers[topic] = []

    def _record_run(self, topic: str, rows: int, status: str, error: str) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.client.insert(
            "raw.ingestion_runs",
            [[uuid4(), f"kafka:{topic}", now, now, status, rows, error]],
            column_names=RUN_COLUMNS,
        )

    def _send_to_dlq(self, message: Message, error: Exception) -> None:
        payload = {
            "error": str(error),
            "topic": message.topic(),
            "partition": message.partition(),
            "offset": message.offset(),
            "key": message.key().decode() if message.key() else None,
            "value": message.value().decode(errors="replace") if message.value() else None,
        }
        self.dlq.produce(
            message.topic() + DLQ_SUFFIX, value=json.dumps(payload).encode()
        )
        self.dlq.poll(0)
        print(f"  -> {message.topic()}{DLQ_SUFFIX}: {error}", file=sys.stderr)

    # -- backpressure helpers ---------------------------------------------

    def _pause(self) -> None:
        partitions = self.consumer.assignment()
        if partitions:
            self.consumer.pause(partitions)

    def _resume(self) -> None:
        partitions = self.consumer.assignment()
        if partitions:
            self.consumer.resume(partitions)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wikipulse-sink",
        description="Consume events from Redpanda and write them to ClickHouse.",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--flush-interval", type=float, default=5.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--high-watermark", type=int, default=5000)
    args = parser.parse_args(argv)

    sink = Sink(
        Settings.from_env(),
        batch_size=args.batch_size,
        flush_interval=args.flush_interval,
        max_retries=args.max_retries,
        high_watermark=args.high_watermark,
    )
    signal.signal(signal.SIGINT, sink.stop)
    signal.signal(signal.SIGTERM, sink.stop)
    sink.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
