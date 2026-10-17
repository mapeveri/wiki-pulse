{{ config(materialized='view') }}

-- Clean daily audience per article. FINAL + GROUP BY guarantees a single row
-- per key even if the ReplacingMergeTree has not merged duplicates yet.

select
    project,
    article,
    access,
    agent,
    granularity,
    ts as event_date,
    sum(views) as views
from {{ source('raw', 'pageviews') }} final
group by
    project,
    article,
    access,
    agent,
    granularity,
    event_date
