import type { Overview } from '../types'
import { formatNumber } from '../format'

export function StatCards({ overview }: { overview: Overview }) {
  const cards = [
    { label: 'Tracked articles', value: formatNumber(overview.articles) },
    { label: 'Total views', value: formatNumber(overview.total_views) },
    { label: 'Avg. daily views', value: formatNumber(overview.avg_daily_views) },
  ]

  return (
    <section className="cards">
      {cards.map((card) => (
        <div className="card stat" key={card.label}>
          <span className="stat-value">{card.value}</span>
          <span className="stat-label">{card.label}</span>
        </div>
      ))}
    </section>
  )
}
