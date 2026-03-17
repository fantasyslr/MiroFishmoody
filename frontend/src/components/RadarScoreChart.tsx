import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { BarChart3 } from 'lucide-react'

const COLORS = ['#6366f1', '#f43f5e', '#10b981', '#f59e0b', '#8b5cf6']

const DEFAULT_DIMENSION_LABELS: Record<string, string> = {
  thumb_stop: '停留吸引力',
  clarity: '信息清晰度',
  trust: '信任感',
  conversion_readiness: '转化就绪度',
  claim_risk: '声称风险',
}

type RadarScoreChartProps = {
  campaigns: Array<{
    name: string
    dimensions: Record<string, number>
  }>
  dimensionLabels?: Record<string, string>
}

export function RadarScoreChart({ campaigns, dimensionLabels }: RadarScoreChartProps) {
  const labels = dimensionLabels ?? DEFAULT_DIMENSION_LABELS

  // Derive all dimension keys from union of campaigns
  const dimensionKeys = Array.from(
    new Set(campaigns.flatMap((c) => Object.keys(c.dimensions)))
  )

  // Transform to recharts format
  const data = dimensionKeys.map((key) => {
    const entry: Record<string, string | number> = {
      dimension: labels[key] ?? key,
    }
    for (const campaign of campaigns) {
      entry[campaign.name] = campaign.dimensions[key] ?? 0
    }
    return entry
  })

  if (campaigns.length === 0) return null

  return (
    <div className="lab-card p-6">
      <h3 className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
        <BarChart3 className="h-5 w-5 text-accent" />
        多维度评分对比
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12 }} />
          <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fontSize: 10 }} />
          {campaigns.map((campaign, i) => (
            <Radar
              key={campaign.name}
              name={campaign.name}
              dataKey={campaign.name}
              stroke={COLORS[i % COLORS.length]}
              fill={COLORS[i % COLORS.length]}
              fillOpacity={0.15}
            />
          ))}
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
