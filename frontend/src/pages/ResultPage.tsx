import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import {
  getLatestReviewSession,
  getResult,
  saveLatestReviewSession,
  type EvaluationResult,
} from '../lib/api'

const verdictTone = {
  ship: 'done',
  revise: 'neutral',
  kill: 'warning',
} as const

const verdictLabel = {
  ship: '建议优先测试',
  revise: '建议继续优化',
  kill: '建议停止推进',
} as const

function percent(value: number) {
  return `${Math.round(value * 100)}%`
}

function LevelMeter({ level }: { level: 1 | 2 | 3 }) {
  return (
    <div className="flex items-center gap-1.5">
      {[1, 2, 3].map((item) => (
        <span
          key={item}
          className={`h-2 rounded-full transition-all duration-300 ${
            item <= level ? 'w-9 bg-coffee' : 'w-6 bg-stone/60'
          }`}
        />
      ))}
      <span className="ml-2 text-xs font-semibold text-ink/50">{level}/3</span>
    </div>
  )
}

function probabilityToLevel(value: number): 1 | 2 | 3 {
  if (value >= 0.5) {
    return 3
  }
  if (value >= 0.25) {
    return 2
  }
  return 1
}

export function ResultPage() {
  const [searchParams] = useSearchParams()
  const latest = getLatestReviewSession()
  const setId = searchParams.get('setId') ?? latest?.setId ?? ''

  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(Boolean(setId))

  useEffect(() => {
    if (!setId) {
      return
    }

    let cancelled = false

    const load = async () => {
      try {
        setLoading(true)
        const nextResult = await getResult(setId)
        if (cancelled) return
        setResult(nextResult)
        setError('')
        saveLatestReviewSession({
          taskId: latest?.taskId,
          setId,
          reviewName: latest?.reviewName,
        })
      } catch (loadError) {
        if (cancelled) return
        setError(loadError instanceof Error ? loadError.message : '加载结果失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [latest?.reviewName, latest?.taskId, setId])

  const probabilityRows = useMemo(() => {
    return result?.probability_board?.campaigns ?? []
  }, [result])

  if (!setId) {
    return (
      <SectionCard
        title="结果页"
        eyebrow="还没有结果"
        description="请先完成一次评审任务，再来查看真实排序与结论。"
      >
        <div className="space-y-4">
          <p className="text-sm leading-7 text-ink/80">
            当前没有可读取的 `setId`。从新建评审页发起任务并等待完成后，这里会显示真实结果。
          </p>
          <Link className="primary-button" to="/new-review">
            去新建评审
          </Link>
        </div>
      </SectionCard>
    )
  }

  if (loading) {
    return (
      <SectionCard
        title="结果页"
        eyebrow="正在加载"
        description="页面正在从后端读取真实评审结果。"
      >
        <p className="text-sm leading-7 text-ink/80">请稍等片刻...</p>
      </SectionCard>
    )
  }

  if (error || !result) {
    return (
      <SectionCard
        title="结果页"
        eyebrow="读取失败"
        description="结果还不可用，可能是任务尚未完成，或后端服务未启动。"
      >
        <div className="space-y-4">
          <div className="rounded-3xl border border-wine/20 bg-wine/10 px-4 py-4 text-sm leading-6 text-wine">
            {error || '未读取到评审结果'}
          </div>
          <div className="flex flex-wrap gap-3">
            <Link className="secondary-button" to={`/running?taskId=${latest?.taskId ?? ''}&setId=${setId}`}>
              回运行状态页
            </Link>
            <Link className="primary-button" to="/new-review">
              发起新评审
            </Link>
          </div>
        </div>
      </SectionCard>
    )
  }

  const lead = probabilityRows[0]

  return (
    <div className="space-y-8">
      <section className="rounded-panel border border-line bg-paper/95 p-6 shadow-paper sm:p-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="section-label">结果页</p>
              <StatusBadge label="真实结果" tone="done" />
            </div>
            <h2 className="mt-3 font-serif text-3xl font-semibold text-coffee sm:text-4xl">
              {lead ? `建议优先测试 ${lead.campaign_name}` : '评审结果已生成'}
            </h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/85">
              {result.summary}
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Link className="primary-button justify-center" to={`/history?setId=${result.set_id}`}>
              去做结算
            </Link>
            <Link className="secondary-button justify-center" to={`/running?taskId=${latest?.taskId ?? ''}&setId=${result.set_id}`}>
              回运行状态
            </Link>
            <Link className="secondary-button justify-center" to="/new-review">
              发起新评审
            </Link>
          </div>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          <div className="rounded-panel border border-line/70 bg-cream px-4 py-4">
            <p className="field-label">评审集</p>
            <p className="mt-3 text-sm font-semibold text-coffee">{result.set_id}</p>
          </div>
          <div className="rounded-panel border border-line/70 bg-cream px-4 py-4">
            <p className="field-label">领先方案概率</p>
            <p className="mt-3 text-sm font-semibold text-coffee">
              {lead ? percent(lead.win_probability) : '暂无'}
            </p>
          </div>
          <div className="rounded-panel border border-line/70 bg-cream px-4 py-4">
            <p className="field-label">不确定性提示</p>
            <p className="mt-3 text-sm leading-6 text-ink/80">
              {result.probability_board?.rationale_for_uncertainty ?? '暂无'}
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <SectionCard
          title="方案排序"
          eyebrow="真实排序"
          description="这里直接读取后端 rank / verdict / objections / strengths，不再展示静态示例。"
        >
          <div className="space-y-4">
            {result.rankings.map((ranking, index) => (
              <article key={ranking.campaign_id} className={`rounded-panel border px-4 py-4 transition-colors ${
                index === 0 ? 'border-coffee/20 bg-coffee/5' : 'border-line/80 bg-cream'
              }`}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-4">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line/70 bg-paper font-serif text-lg font-semibold text-coffee">
                      {ranking.rank}
                    </span>
                    <div>
                      <p className="text-lg font-semibold text-coffee">{ranking.campaign_name}</p>
                      <p className="mt-1 text-sm leading-6 text-ink/80">
                        Panel {ranking.panel_avg.toFixed(1)} · Pairwise {ranking.pairwise_wins} 胜 {ranking.pairwise_losses} 负
                      </p>
                    </div>
                  </div>
                  <StatusBadge label={verdictLabel[ranking.verdict]} tone={verdictTone[ranking.verdict]} />
                </div>

                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  <div className="rounded-3xl border border-line/70 bg-paper px-4 py-3">
                    <p className="field-label">值得保留</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {ranking.top_strengths.length > 0 ? ranking.top_strengths.map((item) => (
                        <span key={item} className="tag-chip">
                          {item}
                        </span>
                      )) : <span className="text-sm text-ink/60">暂无</span>}
                    </div>
                  </div>
                  <div className="rounded-3xl border border-line/70 bg-paper px-4 py-3">
                    <p className="field-label">需要注意</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {ranking.top_objections.length > 0 ? ranking.top_objections.map((item) => (
                        <span key={item} className="tag-chip tag-chip-warning">
                          {item}
                        </span>
                      )) : <span className="text-sm text-ink/60">暂无</span>}
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="系统摘要"
          eyebrow="结果收口"
          description="这里展示后端 summary / assumptions / confidence_notes。"
        >
          <div className="space-y-4">
            <div className="rounded-3xl border border-mist/25 bg-mist-soft/45 px-4 py-4">
              <p className="font-semibold text-coffee">结论摘要</p>
              <p className="mt-2 text-sm leading-7 text-ink/80">{result.summary}</p>
            </div>

            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="font-semibold text-coffee">假设前提</p>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-ink/80">
                {result.assumptions.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>

            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="font-semibold text-coffee">置信提醒</p>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-ink/80">
                {result.confidence_notes.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <SectionCard
          title="概率差异"
          eyebrow="相对强弱"
          description="这里直接读后端 probability board；不把相对概率包装成经营真值。"
        >
          <div className="space-y-3">
            {probabilityRows.map((item) => (
              <div key={item.campaign_id} className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-semibold text-coffee">{item.campaign_name}</p>
                  <StatusBadge label={`${percent(item.win_probability)} 胜出概率`} tone={verdictTone[item.verdict]} />
                </div>
                <p className="mt-2 text-sm leading-6 text-ink/80">{item.verdict_rationale}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard
            title="子市场概率"
            eyebrow="辅助阅读"
            description="用三档强弱展示子市场概率，方便非技术同事快速看差异。"
          >
            <div className="space-y-3">
              {probabilityRows.map((item) => (
                <div key={item.campaign_id} className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                  <p className="font-semibold text-coffee">{item.campaign_name}</p>
                  <div className="mt-3 space-y-3">
                    {Object.entries(item.sub_markets ?? {}).map(([market, value]) => (
                      <div key={market} className="rounded-3xl border border-line/70 bg-paper px-4 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-coffee">{market}</p>
                          <LevelMeter level={probabilityToLevel(value)} />
                        </div>
                        <p className="mt-2 text-sm leading-6 text-ink/80">{percent(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            title="下一步"
            eyebrow="接下来做什么"
            description="团队看完结果后，下一步应该回到真实结算，而不是继续分析。"
          >
            <div className="space-y-3">
              <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
                如果要验证这次建议，请去结算页回填真实赢家和投放指标。
              </div>
              <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
                如果当前结果没有明显优势，请回到新建评审页补充方案差异后再跑一次。
              </div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
