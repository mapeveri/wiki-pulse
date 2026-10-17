"""Metrics endpoints backed by the dbt mart layer."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .. import db
from ..models import (
    ArticleSummary,
    ArticleTimeseries,
    CorrelationPoint,
    Overview,
    TopMover,
    TrendPoint,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Columns that may be used in ORDER BY. Kept as a whitelist so the sort
# parameter can never be used to inject SQL.
SORTABLE_COLUMNS = {
    "article",
    "total_views",
    "avg_daily_views",
    "views_change_pct_7d",
    "word_count",
}


@router.get("/overview", response_model=Overview)
def overview() -> Overview:
    """High level totals for the dashboard header."""
    rows = db.query(
        """
        select
            count()                          as articles,
            sum(total_views)                 as total_views,
            round(avg(avg_daily_views), 2)   as avg_daily_views
        from mart_article_traffic
        """
    )
    return rows[0]


@router.get("/articles", response_model=list[ArticleSummary])
def list_articles(
    sort: str = Query("total_views"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
) -> list[ArticleSummary]:
    """All tracked articles with audience and content metrics."""
    if sort not in SORTABLE_COLUMNS:
        raise HTTPException(status_code=400, detail=f"invalid sort column: {sort}")

    return db.query(
        f"""
        select
            article, title, total_views, avg_daily_views,
            views_last_7d, views_prev_7d, views_change_pct_7d,
            word_count, section_count, internal_links, external_links
        from mart_article_traffic
        order by {sort} {order.upper()}
        limit {{limit:UInt32}}
        """,
        {"limit": limit},
    )


@router.get("/articles/{article}/timeseries", response_model=ArticleTimeseries)
def article_timeseries(article: str) -> ArticleTimeseries:
    """Daily audience for a single article."""
    rows = db.query(
        """
        select event_date, views
        from fct_article_daily_traffic
        where article = {article:String}
        order by event_date
        """,
        {"article": article},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="article not found")
    return {"article": article, "points": rows}


@router.get("/top-movers", response_model=list[TopMover])
def top_movers(
    direction: str = Query("up", pattern="^(up|down)$"),
    limit: int = Query(5, ge=1, le=100),
) -> list[TopMover]:
    """Articles with the largest week-over-week audience change."""
    order = "DESC" if direction == "up" else "ASC"
    return db.query(
        f"""
        select article, title, views_last_7d, views_prev_7d, views_change_pct_7d
        from mart_article_traffic
        where views_change_pct_7d is not null
        order by views_change_pct_7d {order}
        limit {{limit:UInt32}}
        """,
        {"limit": limit},
    )


@router.get("/trends", response_model=list[TrendPoint])
def trends() -> list[TrendPoint]:
    """Total daily audience across all tracked articles."""
    return db.query(
        """
        select event_date, sum(views) as views
        from fct_article_daily_traffic
        group by event_date
        order by event_date
        """
    )


@router.get("/correlation", response_model=list[CorrelationPoint])
def correlation() -> list[CorrelationPoint]:
    """Points to explore the relationship between content size and audience."""
    return db.query(
        """
        select article, title, word_count, total_views
        from mart_article_traffic
        where word_count is not null
        order by total_views desc
        """
    )
