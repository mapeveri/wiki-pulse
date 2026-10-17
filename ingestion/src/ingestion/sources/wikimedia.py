"""Wikimedia Pageviews API client.

The API is public and requires no key, but Wikimedia asks for a descriptive
``User-Agent`` header. See https://wikitech.wikimedia.org/wiki/Analytics/AQS/Pageviews
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import quote

import httpx

BASE_URL = "https://wikimedia.org/api/rest_v1"


@dataclass(frozen=True)
class PageviewRecord:
    project: str
    article: str
    access: str
    agent: str
    granularity: str
    ts: date
    views: int


def _parse_timestamp(timestamp: str, granularity: str) -> date:
    """Convert an API timestamp to a date.

    Daily timestamps look like ``2024010100`` and monthly ones like ``20240100``
    (the trailing digits depend on the granularity).
    """
    if granularity == "monthly":
        return datetime.strptime(timestamp[:6], "%Y%m").date()
    return datetime.strptime(timestamp[:8], "%Y%m%d").date()


def fetch_pageviews(
    *,
    client: httpx.Client,
    project: str,
    article: str,
    start: str,
    end: str,
    access: str = "all-access",
    agent: str = "user",
    granularity: str = "daily",
) -> list[PageviewRecord]:
    """Fetch daily/monthly pageviews for a single article.

    ``start`` and ``end`` use ``YYYYMMDD`` for daily data and ``YYYYMM`` for
    monthly data. Returns an empty list when the API has no data for the range.
    """
    url = (
        f"{BASE_URL}/metrics/pageviews/per-article/"
        f"{project}/{access}/{agent}/{quote(article, safe='')}/"
        f"{granularity}/{start}/{end}"
    )
    response = client.get(url)
    if response.status_code == 404:
        return []
    response.raise_for_status()

    records: list[PageviewRecord] = []
    for item in response.json().get("items", []):
        records.append(
            PageviewRecord(
                project=item["project"],
                article=item["article"],
                access=item["access"],
                agent=item["agent"],
                granularity=item["granularity"],
                ts=_parse_timestamp(item["timestamp"], granularity),
                views=int(item["views"]),
            )
        )
    return records
