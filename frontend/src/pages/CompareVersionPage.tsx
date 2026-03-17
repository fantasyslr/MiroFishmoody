import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getVersionCompare, type VersionCompareResult } from '../lib/api'
import { ArrowLeft, Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const DIMENSION_LABELS: Record<string, string> = {
  thumb_stop: '停留吸引力',
  clarity: '信息清晰度',
  trust: '信任感',
  conversion_readiness: '转化就绪度',
  claim_risk: '声称风险',
}

export function CompareVersionPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const v1 = searchParams.get('v1') ?? ''
  const v2 = searchParams.get('v2') ?? ''

  const [data, setData] = useState<VersionCompareResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!v1 || !v2) {
      setError('缺少版本参数')
      setLoading(false)
      return
    }
    getVersionCompare(v1, v2)
      .then(setData)
      .catch(e => setError(e.message ?? '加载失败'))
      .finally(() => setLoading(false))
  }, [v1, v2])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 text-primary animate-spin" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <button onClick={() => navigate(-1)} className="lab-button lab-button-outline flex items-center gap-2 text-sm">
          <ArrowLeft className="h-4 w-4" /> 返回
        </button>
        <div className="lab-card p-6 text-center text-muted-foreground">
          {error ?? '无法加载对比数据'}
        </div>
      </div>
    )
  }

  const { v1: ver1, v2: ver2, deltas } = data
  const campaigns1 = ver1.scoreboard?.campaigns ?? []
  const campaigns2 = ver2.scoreboard?.campaigns ?? []

  // Build name-indexed maps
  const map1 = Object.fromEntries(campaigns1.map(c => [c.campaign_name, c]))
  const map2 = Object.fromEntries(campaigns2.map(c => [c.campaign_name, c]))
  const allNames = Array.from(new Set([...campaigns1.map(c => c.campaign_name), ...campaigns2.map(c => c.campaign_name)]))

  return (
    <div className="space-y-12 pb-20 animate-in fade-in duration-700">

      {/* Header */}
      <section className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl text-primary font-semibold mb-2">版本对比</h1>
            <p className="text-muted-foreground max-w-2xl text-balance">
              版本 {ver1.version} vs 版本 {ver2.version} -- 并排展示评分变化与维度差异
            </p>
          </div>
          <button onClick={() => navigate(-1)} className="lab-button lab-button-outline flex items-center gap-2 text-sm">
            <ArrowLeft className="h-4 w-4" /> 返回
          </button>
        </div>
      </section>

      {/* Side-by-side comparison per campaign */}
      {allNames.map(name => {
        const c1 = map1[name]
        const c2 = map2[name]
        const delta = deltas[name]

        return (
          <section key={name} className="space-y-4">
            <h2 className="font-display text-xl text-primary border-b border-border pb-3">{name}</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* V1 Column */}
              <div className="lab-card p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                    版本 {ver1.version}
                  </h3>
                  {c1 && (
                    <span className="font-mono text-lg font-medium">{c1.overall_score.toFixed(2)}</span>
                  )}
                </div>
                {c1 && (
                  <div className="space-y-2">
                    {Object.entries(c1.dimension_scores).map(([dk, score]) => (
                      <div key={dk} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{DIMENSION_LABELS[dk] ?? dk}</span>
                        <span className="font-mono">{score.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
                {!c1 && <p className="text-sm text-muted-foreground">此版本无该方案</p>}
              </div>

              {/* V2 Column */}
              <div className="lab-card p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                    版本 {ver2.version}
                  </h3>
                  {c2 && (
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-lg font-medium">{c2.overall_score.toFixed(2)}</span>
                      {delta && <DeltaBadge value={delta.overall_delta} />}
                    </div>
                  )}
                </div>
                {c2 && (
                  <div className="space-y-2">
                    {Object.entries(c2.dimension_scores).map(([dk, score]) => (
                      <div key={dk} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{DIMENSION_LABELS[dk] ?? dk}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{score.toFixed(2)}</span>
                          {delta?.dimension_deltas[dk] != null && (
                            <DeltaBadge value={delta.dimension_deltas[dk]} />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {!c2 && <p className="text-sm text-muted-foreground">此版本无该方案</p>}
              </div>
            </div>
          </section>
        )
      })}
    </div>
  )
}

function DeltaBadge({ value }: { value: number }) {
  if (Math.abs(value) < 0.001) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs text-gray-400">
        <Minus className="h-3 w-3" /> 0
      </span>
    )
  }
  if (value > 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs text-green-600 font-medium">
        <TrendingUp className="h-3 w-3" /> +{value.toFixed(3)}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-0.5 text-xs text-red-600 font-medium">
      <TrendingDown className="h-3 w-3" /> {value.toFixed(3)}
    </span>
  )
}
