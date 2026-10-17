{{ config(materialized='table') }}

-- Fact table at the granularity of (article, day): audience joined with the
-- content metrics of the same article. This is the base for the time series
-- and for the aggregates in marts.

select
    p.project,
    p.article,
    p.event_date,
    p.views,
    a.word_count,
    a.section_count,
    a.internal_links,
    a.external_links
from {{ ref('stg_pageviews') }} p
left join {{ ref('dim_articles') }} a
    on p.project = a.project
   and p.article = a.article
