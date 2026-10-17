import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { TrendPoint } from '../types'
import { formatCompact } from '../format'

export function TrendsChart({ data }: { data: TrendPoint[] }) {
  return (
    <div className="card">
      <h2>Total audience per day</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#26304a" />
          <XAxis dataKey="event_date" tick={{ fontSize: 11, fill: '#93a1c4' }} minTickGap={24} />
          <YAxis
            tick={{ fontSize: 11, fill: '#93a1c4' }}
            tickFormatter={(value: number) => formatCompact(value)}
          />
          <Tooltip
            contentStyle={{ background: '#131a2b', border: '1px solid #26304a', borderRadius: 8 }}
            labelStyle={{ color: '#93a1c4' }}
          />
          <Line
            type="monotone"
            dataKey="views"
            stroke="#5b8cff"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
