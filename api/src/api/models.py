"""Pydantic response models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Health(BaseModel):
    status: str


class Overview(BaseModel):
    articles: int
    total_views: int
    avg_daily_views: float


class ArticleSummary(BaseModel):
    article: str
    title: str | None = None
    total_views: int
    avg_daily_views: float
    views_last_7d: int
    views_prev_7d: int
    views_change_pct_7d: float | None = None
    word_count: int | None = None
    section_count: int | None = None
    internal_links: int | None = None
    external_links: int | None = None


class TopMover(BaseModel):
    article: str
    title: str | None = None
    views_last_7d: int
    views_prev_7d: int
    views_change_pct_7d: float


class TimeseriesPoint(BaseModel):
    event_date: date
    views: int


class ArticleTimeseries(BaseModel):
    article: str
    points: list[TimeseriesPoint]


class TrendPoint(BaseModel):
    event_date: date
    views: int


class CorrelationPoint(BaseModel):
    article: str
    title: str | None = None
    word_count: int | None = None
    total_views: int
