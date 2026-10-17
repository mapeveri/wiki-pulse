{{ config(materialized='table') }}

-- Per-article summary that powers the dashboard overview and top-movers table.
-- "current" is the last 7 days of available data; "previous" is the 7 days
-- before that. Change is measured week over week.

with bounds as (

    select max(event_date) as max_date
    from {{ ref('fct_article_daily_traffic') }}

),

totals as (

    select
        project,
        article,
        sum(views)             as total_views,
        round(avg(views), 2)   as avg_daily_views,
        min(event_date)        as first_date,
        max(event_date)        as last_date,
        sumIf(views, event_date > (select max_date from bounds) - 7) as views_last_7d,
        sumIf(
            views,
            event_date > (select max_date from bounds) - 14
            and event_date <= (select max_date from bounds) - 7
        ) as views_prev_7d
    from {{ ref('fct_article_daily_traffic') }}
    group by
        project,
        article

)

select
    d.project,
    d.article,
    a.title,
    d.total_views,
    d.avg_daily_views,
    d.first_date,
    d.last_date,
    d.views_last_7d,
    d.views_prev_7d,
    d.views_last_7d - d.views_prev_7d as views_delta_7d,
    if(
        d.views_prev_7d = 0,
        cast(null as Nullable(Float64)),
        round((d.views_last_7d - d.views_prev_7d) / d.views_prev_7d * 100, 2)
    ) as views_change_pct_7d,
    a.word_count,
    a.section_count,
    a.internal_links,
    a.external_links
from totals d
left join {{ ref('dim_articles') }} a
    on d.project = a.project
   and d.article = a.article
order by d.total_views desc
