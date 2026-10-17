import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'

import type { CorrelationPoint } from '../types'
import { formatCompact } from '../format'

export function CorrelationScatter({ data }: { data: CorrelationPoint[] }) {
  return (
    <div className="card">
      <h2>Content size vs. audience</h2>
      <p className="muted">
        Each point is an article: word count (x) against total views (y).
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#26304a" />
          <XAxis
            type="number"
            dataKey="word_count"
            name="Words"
            tick={{ fontSize: 11, fill: '#93a1c4' }}
            tickFormatter={(value: number) => formatCompact(value)}
          />
          <YAxis
            type="number"
            dataKey="total_views"
            name="Total views"
            tick={{ fontSize: 11, fill: '#93a1c4' }}
            tickFormatter={(value: number) => formatCompact(value)}
          />
          <ZAxis range={[70, 70]} />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            contentStyle={{ background: '#131a2b', border: '1px solid #26304a', borderRadius: 8 }}
            formatter={(value: number) => formatCompact(value)}
          />
          <Scatter data={data} fill="#4fd1a5" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
