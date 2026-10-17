"""Command line interface for the ingestion jobs.

These jobs are producers: they fetch data from the sources and publish one event
per record to Redpanda. The sink (see ``ingestion.sink``) is the only component
that writes to ClickHouse.

Examples:
    wikipulse-ingest pageviews --start 20260101 --end 20260131
    wikipulse-ingest pageviews --start 20260101 --end 20260131 \
        --articles Python_(programming_language) Kubernetes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx
from confluent_kafka import KafkaException

from .config import Settings
from .kafka import PAGEVIEWS_TOPIC, get_producer
from .sources.wikimedia import fetch_pageviews

DEFAULT_PROJECT = "en.wikipedia"


def _read_topics(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Topics file not found: {path}")
    topics: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            topics.append(line)
    return topics


def _ingest_pageviews(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    topics = args.articles or _read_topics(Path(args.topics_file))
    if not topics:
        print("No topics to ingest.", file=sys.stderr)
        return 1

    producer = get_producer(settings.kafka)
    counts = {"produced": 0, "failed": 0}

    def on_delivery(error, _message) -> None:
        counts["produced" if error is None else "failed"] += 1

    try:
        with httpx.Client(
            headers={"User-Agent": settings.wikimedia_user_agent}, timeout=30.0
        ) as http:
            for article in topics:
                records = fetch_pageviews(
                    client=http,
                    project=args.project,
                    article=article,
                    start=args.start,
                    end=args.end,
                    access=args.access,
                    agent=args.agent,
                    granularity=args.granularity,
                )
                print(f"  {article}: {len(records)} records")
                for record in records:
                    event = {
                        "project": record.project,
                        "article": record.article,
                        "access": record.access,
                        "agent": record.agent,
                        "granularity": record.granularity,
                        "ts": record.ts.isoformat(),
                        "views": record.views,
                    }
                    producer.produce(
                        PAGEVIEWS_TOPIC,
                        key=record.article.encode(),
                        value=json.dumps(event).encode(),
                        callback=on_delivery,
                    )
                    # Serve delivery callbacks and keep the internal queue bounded.
                    producer.poll(0)
    except KafkaException as exc:
        print(f"Kafka error: {exc}", file=sys.stderr)
        return 1
    finally:
        producer.flush()

    print(
        f"Produced {counts['produced']} events to {PAGEVIEWS_TOPIC} "
        f"({counts['failed']} failed)"
    )
    return 0 if counts["failed"] == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wikipulse-ingest",
        description="Publish audience and content data to Redpanda.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    default_topics = Path(__file__).resolve().parents[2] / "topics.txt"

    pv = sub.add_parser("pageviews", help="Publish Wikimedia Pageviews to Redpanda")
    pv.add_argument("--start", required=True, help="Start date inclusive (YYYYMMDD)")
    pv.add_argument("--end", required=True, help="End date inclusive (YYYYMMDD)")
    pv.add_argument("--project", default=DEFAULT_PROJECT, help="Wikimedia project (default: en.wikipedia)")
    pv.add_argument("--articles", nargs="+", help="Article titles (overrides the topics file)")
    pv.add_argument("--topics-file", default=str(default_topics), help="File with one article per line")
    pv.add_argument("--access", default="all-access")
    pv.add_argument("--agent", default="user")
    pv.add_argument("--granularity", default="daily", choices=["daily", "monthly"])
    pv.set_defaults(func=_ingest_pageviews)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
