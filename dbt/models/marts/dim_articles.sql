{{ config(materialized='table') }}

-- One row per tracked article with its content metrics.

select
    project,
    article,
    title,
    url,
    word_count,
    section_count,
    internal_links,
    external_links,
    crawled_at
from {{ ref('stg_articles') }}
