export interface Overview {
  articles: number
  total_views: number
  avg_daily_views: number
}

export interface TopMover {
  article: string
  title: string | null
  views_last_7d: number
  views_prev_7d: number
  views_change_pct_7d: number
}

export interface TrendPoint {
  event_date: string
  views: number
}

export interface ArticleSummary {
  article: string
  title: string | null
  total_views: number
  avg_daily_views: number
  views_last_7d: number
  views_prev_7d: number
  views_change_pct_7d: number | null
  word_count: number | null
  section_count: number | null
  internal_links: number | null
  external_links: number | null
}

export interface CorrelationPoint {
  article: string
  title: string | null
  word_count: number | null
  total_views: number
}
