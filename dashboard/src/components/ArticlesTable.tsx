import { useState } from 'react'

import { api } from '../api'
import { useApi } from '../useApi'
import { formatNumber, formatPct } from '../format'

interface Column {
  key: string
  label: string
  numeric?: boolean
}

const COLUMNS: Column[] = [
  { key: 'article', label: 'Article' },
  { key: 'total_views', label: 'Total views', numeric: true },
  { key: 'views_change_pct_7d', label: '7d change', numeric: true },
  { key: 'word_count', label: 'Words', numeric: true },
]

export function ArticlesTable() {
  const [sort, setSort] = useState('total_views')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  const { data, loading, error } = useApi(() => api.articles(sort, order), [sort, order])

  function toggleSort(key: string) {
    if (key === sort) {
      setOrder(order === 'asc' ? 'desc' : 'asc')
    } else {
      setSort(key)
      setOrder('desc')
    }
  }

  return (
    <div className="card">
      <h2>Articles</h2>
      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error}</p>}
      {data && (
        <table>
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  className={column.numeric ? 'numeric sortable' : 'sortable'}
                  onClick={() => toggleSort(column.key)}
                >
                  {column.label}
                  {sort === column.key ? (order === 'asc' ? ' ▲' : ' ▼') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.article}>
                <td>{row.title ?? row.article}</td>
                <td className="numeric">{formatNumber(row.total_views)}</td>
                <td
                  className={
                    row.views_change_pct_7d === null
                      ? 'numeric'
                      : row.views_change_pct_7d >= 0
                        ? 'numeric delta up'
                        : 'numeric delta down'
                  }
                >
                  {formatPct(row.views_change_pct_7d)}
                </td>
                <td className="numeric">{row.word_count ? formatNumber(row.word_count) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
