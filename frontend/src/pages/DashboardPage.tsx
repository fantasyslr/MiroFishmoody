import { useEffect, useState } from 'react'
import { getBrandictionStats } from '../lib/api'
import { Database, TrendingUp, AlertCircle } from 'lucide-react'

export function DashboardPage() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    getBrandictionStats().then(setStats)
  }, [])

  if (!stats) return <div className="p-6">正在加载数据...</div>

  return (
    <div className="space-y-12">
      <section className="space-y-4">
        <h1 className="font-display text-4xl text-primary font-semibold">数据总览</h1>
        <p className="text-muted-foreground text-lg max-w-2xl text-balance">
          Brandiction 引擎 v3 的系统就绪状态与经验数据覆盖情况。
        </p>
      </section>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="lab-card p-6">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">已索引干预</div>
          <div className="font-display text-4xl text-primary">{stats.interventions_count?.toLocaleString()}</div>
        </div>
        <div className="lab-card p-6">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">已追踪结果</div>
          <div className="font-display text-4xl text-primary">{stats.outcomes_count?.toLocaleString()}</div>
        </div>
        <div className="lab-card p-6">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">品牌信号</div>
          <div className="font-display text-4xl text-primary">{stats.signals_count?.toLocaleString()}</div>
        </div>
        <div className="lab-card p-6">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">竞品事件</div>
          <div className="font-display text-4xl text-primary">{stats.competitor_events_count?.toLocaleString()}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        <section className="space-y-4">
          <h2 className="font-display text-2xl text-primary flex items-center gap-2">
            <Database className="h-5 w-5" /> 市场覆盖
          </h2>
          <div className="lab-card p-6 space-y-4">
            {Object.entries(stats.market_coverage || {}).map(([market, ratio]) => (
              <div key={market} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="uppercase">{market}</span>
                  <span className="font-mono text-muted-foreground">{((ratio as number) * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1 bg-border rounded-full overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: `${(ratio as number) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="font-display text-2xl text-primary flex items-center gap-2">
            <TrendingUp className="h-5 w-5" /> 平台覆盖
          </h2>
          <div className="lab-card p-6 space-y-4">
            {Object.entries(stats.platform_coverage || {}).map(([platform, ratio]) => (
              <div key={platform} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="capitalize">{platform}</span>
                  <span className="font-mono text-muted-foreground">{((ratio as number) * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1 bg-border rounded-full overflow-hidden">
                  <div className="h-full bg-secondary-foreground" style={{ width: `${(ratio as number) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>

      <section className="space-y-4">
        <h2 className="font-display text-2xl text-primary flex items-center gap-2 text-accent">
          <AlertCircle className="h-5 w-5" /> 稀疏度预警
        </h2>
        <div className="lab-card p-6 bg-accent/5 border-accent/20">
          <p className="text-sm mb-4">以下认知维度的历史干预证据有限，模型假设的置信度会较低。</p>
          <div className="flex gap-2">
            {((stats.weakest_dimensions as string[]) || []).map((dim: string) => (
              <span key={dim} className="text-xs uppercase tracking-wider font-semibold text-accent border border-accent/30 px-2 py-1 rounded-sm bg-background">
                {dim.replace('_', ' ')}
              </span>
            ))}
          </div>
        </div>
      </section>

    </div>
  )
}
