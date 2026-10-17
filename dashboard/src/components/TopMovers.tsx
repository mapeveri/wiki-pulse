import type { TopMover } from '../types'
import { formatCompact, formatPct } from '../format'

function MoverList({
  title,
  movers,
  positive,
}: {
  title: string
  movers: TopMover[]
  positive: boolean
}) {
  return (
    <div className="mover-list">
      <h3>{title}</h3>
      <ul>
        {movers.map((mover) => (
          <li key={mover.article}>
            <span className="mover-name">{mover.title ?? mover.article}</span>
            <span className={positive ? 'delta up' : 'delta down'}>
              {formatPct(mover.views_change_pct_7d)}
            </span>
            <span className="mover-views">{formatCompact(mover.views_last_7d)} views</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function TopMovers({ up, down }: { up: TopMover[]; down: TopMover[] }) {
  return (
    <div className="card">
      <h2>Top movers (last 7 days)</h2>
      <div className="movers">
        <MoverList title="Gaining" movers={up} positive />
        <MoverList title="Losing" movers={down} positive={false} />
      </div>
    </div>
  )
}
