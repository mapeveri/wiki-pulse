-- Raw tables. They store data exactly as it arrives from the sources.
--
-- ReplacingMergeTree(ingested_at) is used so re-ingesting the same logical row
-- (same ORDER BY key) replaces the previous version instead of duplicating it.
-- Deduplication happens on background merges, so queries that need a guaranteed
-- single row per key should aggregate (or use FINAL) in the staging layer.

-- Daily audience per article, from the Wikimedia Pageviews API.
CREATE TABLE IF NOT EXISTS raw.pageviews
(
    project     LowCardinality(String),
    article     String,
    access      LowCardinality(String),
    agent       LowCardinality(String),
    granularity LowCardinality(String),
    ts          Date,
    views       UInt64,
    ingested_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(ts)
ORDER BY (project, article, ts, access, agent);

-- Content structure per article, from the Go crawler.
CREATE TABLE IF NOT EXISTS raw.articles
(
    project        LowCardinality(String),
    article        String,
    url            String,
    title          String,
    word_count     UInt32,
    section_count  UInt32,
    internal_links UInt32,
    external_links UInt32,
    crawled_at     DateTime,
    ingested_at    DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY (project, article);

-- One row per ingestion run, for observability of the pipelines.
CREATE TABLE IF NOT EXISTS raw.ingestion_runs
(
    run_id      UUID,
    source      LowCardinality(String),
    started_at  DateTime,
    finished_at DateTime,
    status      LowCardinality(String),
    rows_loaded UInt64,
    error       String
)
ENGINE = MergeTree
ORDER BY (source, started_at);
