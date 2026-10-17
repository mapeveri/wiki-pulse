"""Command line interface for the ingestion jobs.

Examples:
    wikipulse-ingest pageviews --start 20260101 --end 20260131
    wikipulse-ingest pageviews --start 20260101 --end 20260131 \
        --articles Python_(programming_language) Kubernetes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from .clickhouse import get_client
from .config import Settings
from .runs import RunTracker
from .sources.wikimedia import fetch_pageviews

DEFAULT_PROJECT = "en.wikipedia"

PAGEVIEW_COLUMNS = [
    "project",
    "article",
    "access",
    "agent",
    "granularity",
    "ts",
    "views",
]


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
    if args.articles:
        topics = args.articles
    else:
        topics = _read_topics(Path(args.topics_file))

    if not topics:
        print("No topics to ingest.", file=sys.stderr)
        return 1

    client = get_client(settings.clickhouse)
    rows: list[list[object]] = []

    with httpx.Client(
        headers={"User-Agent": settings.wikimedia_user_agent}, timeout=30.0
    ) as http, RunTracker(client, "wikimedia.pageviews") as run:
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
            for r in records:
                rows.append(
                    [r.project, r.article, r.access, r.agent, r.granularity, r.ts, r.views]
                )
        if rows:
            client.insert("raw.pageviews", rows, column_names=PAGEVIEW_COLUMNS)
        run.rows_loaded = len(rows)

    print(f"Loaded {len(rows)} rows into raw.pageviews")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wikipulse-ingest",
        description="Load audience and content data into the ClickHouse raw layer.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    default_topics = Path(__file__).resolve().parents[2] / "topics.txt"

    pv = sub.add_parser(
        "pageviews",
        help="Ingest Wikimedia Pageviews into raw.pageviews",
    )
    pv.add_argument("--start", required=True, help="Start date inclusive (YYYYMMDD)")
    pv.add_argument("--end", required=True, help="End date inclusive (YYYYMMDD)")
    pv.add_argument("--project", default=DEFAULT_PROJECT, help="Wikimedia project (default: en.wikipedia)")
    pv.add_argument("--articles", nargs="+", help="Article titles (overrides the topics file)")
    pv.add_argument("--topics-file", default=str(default_topics), help="File with one article per line")
    pv.add_argument("--access", default="all-access")
    pv.add_argument("--agent", default="user")
    pv.add_argument(
        "--granularity", default="daily", choices=["daily", "monthly"]
    )
    pv.set_defaults(func=_ingest_pageviews)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
