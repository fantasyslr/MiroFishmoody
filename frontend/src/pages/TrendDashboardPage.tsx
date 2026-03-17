import { useState, useEffect, useMemo } from 'react'
import { TrendingUp, Loader2, BarChart3 } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { getTrends, type TrendsResponse } from '../lib/api'

const COLORS = [
  '#7c3aed',
  '#2563eb',
  '#059669',
  '#d97706',
  '#dc2626',
  '#8b5cf6',
  '#0891b2',
]

const CATEGORY_OPTIONS = [
  { label: '全部品类', value: 'all' },
  { label: '透明片', value: 'moodyplus' },
  { label: '彩片', value: 'colored_lenses' },
] as const

function formatDate(ts: string) {
  const d = new Date(ts)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}/${day}`
}

export function TrendDashboardPage() {
  const [category, setCategory] = useState('all')
  const [data, setData] = useState<TrendsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = (cat: string) => {
    setLoading(true)
    setError(null)
    getTrends(cat)
      .then(setData)
      .catch((e) => setError(e.message ?? 'Failed to load trends'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchData(category)
  }, [category])

  // Transform data for recharts: each row = { timestamp, 'Campaign A': 7.5, ... }
  const chartData = useMemo(() => {
    if (!data?.data_points) return []
    return data.data_points.map((dp) => ({
      timestamp: formatDate(dp.timestamp),
      ...dp.campaigns,
    }))
  }, [data])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="flex items-center gap-2 font-display text-2xl font-semibold tracking-tight text-primary">
          <TrendingUp className="h-6 w-6 text-accent" />
          推演趋势
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          跨 campaign 追踪推演分数变化趋势
        </p>
      </div>

      {/* Category filter */}
      <div className="flex items-center gap-1">
        {CATEGORY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setCategory(opt.value)}
            className={`rounded-sm px-3 py-1.5 text-sm transition-colors ${
              category === opt.value
                ? 'bg-primary text-primary-foreground font-medium'
                : 'bg-secondary/30 text-muted-foreground hover:bg-secondary/50'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-4 py-20 text-muted-foreground">
          <p>{error}</p>
          <button
            onClick={() => fetchData(category)}
            className="rounded-sm bg-primary px-4 py-2 text-sm text-primary-foreground transition-colors hover:bg-primary/90"
          >
            重试
          </button>
        </div>
      ) : !data?.data_points?.length ? (
        <div className="flex flex-col items-center gap-3 py-20 text-muted-foreground">
          <BarChart3 className="h-10 w-10 opacity-30" />
          <p>暂无推演数据</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-6">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 12 }}
                stroke="hsl(var(--muted-foreground))"
              />
              <YAxis
                domain={[0, 10]}
                tick={{ fontSize: 12 }}
                stroke="hsl(var(--muted-foreground))"
              />
              <Tooltip />
              <Legend />
              {data.campaign_names.map((name, i) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
