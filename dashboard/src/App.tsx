import { api } from './api'
import { useApi } from './useApi'
import { StatCards } from './components/StatCards'
import { TrendsChart } from './components/TrendsChart'
import { TopMovers } from './components/TopMovers'
import { ArticlesTable } from './components/ArticlesTable'
import { CorrelationScatter } from './components/CorrelationScatter'

export default function App() {
  const overview = useApi(() => api.overview(), [])
  const trends = useApi(() => api.trends(), [])
  const up = useApi(() => api.topMovers('up'), [])
  const down = useApi(() => api.topMovers('down'), [])
  const correlation = useApi(() => api.correlation(), [])

  return (
    <div className="page">
      <header className="header">
        <h1>WikiPulse</h1>
        <p className="muted">Audience & content analytics for a curated set of topics</p>
      </header>

      {overview.error && <p className="error">{overview.error}</p>}
      {overview.data && <StatCards overview={overview.data} />}

      {trends.data && <TrendsChart data={trends.data} />}

      <div className="grid">
        {up.data && down.data && <TopMovers up={up.data} down={down.data} />}
        {correlation.data && <CorrelationScatter data={correlation.data} />}
      </div>

      <ArticlesTable />
    </div>
  )
}
