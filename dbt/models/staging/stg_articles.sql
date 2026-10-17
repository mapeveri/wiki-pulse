{{ config(materialized='view') }}

-- Latest content metrics per article. FINAL + GROUP BY keeps one row per
-- article even across multiple crawls.

select
    project,
    article,
    any(url)            as url,
    any(title)          as title,
    max(word_count)     as word_count,
    max(section_count)  as section_count,
    max(internal_links) as internal_links,
    max(external_links) as external_links,
    max(crawled_at)     as crawled_at
from {{ source('raw', 'articles') }} final
group by
    project,
    article
