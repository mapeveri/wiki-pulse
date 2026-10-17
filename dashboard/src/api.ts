import type {
  ArticleSummary,
  CorrelationPoint,
  Overview,
  TopMover,
  TrendPoint,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export const api = {
  overview: () => get<Overview>('/metrics/overview'),
  trends: () => get<TrendPoint[]>('/metrics/trends'),
  topMovers: (direction: 'up' | 'down', limit = 5) =>
    get<TopMover[]>(`/metrics/top-movers?direction=${direction}&limit=${limit}`),
  articles: (sort: string, order: 'asc' | 'desc') =>
    get<ArticleSummary[]>(`/metrics/articles?sort=${sort}&order=${order}&limit=100`),
  correlation: () => get<CorrelationPoint[]>('/metrics/correlation'),
}
