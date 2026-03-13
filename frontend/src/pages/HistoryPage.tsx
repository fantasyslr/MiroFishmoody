import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import {
  getCalibration,
  getLatestReviewSession,
  getResult,
  resolveEvaluation,
  saveLatestReviewSession,
  triggerRecalibrate,
  type CalibrationResponse,
  type EvaluationResult,
} from '../lib/api'

const metricKeys = ['ctr', 'hold_rate', 'lpv', 'cvr', 'roas', 'aov'] as const

export function HistoryPage() {
  const [searchParams] = useSearchParams()
  const latest = getLatestReviewSession()
  const setId = searchParams.get('setId') ?? latest?.setId ?? ''

  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [calibration, setCalibration] = useState<CalibrationResponse | null>(null)
  const [winnerId, setWinnerId] = useState('')
  const [metrics, setMetrics] = useState<Record<string, string>>({})
  const [notes, setNotes] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(Boolean(setId))
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRecalibrating, setIsRecalibrating] = useState(false)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        setLoading(true)
        const [nextCalibration, nextResult] = await Promise.all([
          getCalibration(),
          setId ? getResult(setId) : Promise.resolve(null),
        ])
        if (cancelled) {
          return
        }
        setCalibration(nextCalibration)
        setResult(nextResult)
        setWinnerId(nextResult?.rankings[0]?.campaign_id ?? '')
        setError('')
        if (setId) {
          saveLatestReviewSession({
            taskId: latest?.taskId,
            setId,
            reviewName: latest?.reviewName,
          })
        }
      } catch (loadError) {
        if (cancelled) {
          return
        }
        setError(loadError instanceof Error ? loadError.message : '加载结算页失败')
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [latest?.reviewName, latest?.taskId, setId])

  const handleMetricChange = (key: string, value: string) => {
    setMetrics((current) => ({ ...current, [key]: value }))
  }

  const submitResolution = async () => {
    if (!setId || !winnerId || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setMessage('')
    setError('')

    try {
      const actualMetrics = Object.fromEntries(
        Object.entries(metrics)
          .filter(([, value]) => value.trim() !== '')
          .map(([key, value]) => [key, Number(value)]),
      )

      const response = await resolveEvaluation({
        set_id: setId,
        winner_campaign_id: winnerId,
        actual_metrics: actualMetrics,
        notes: notes.trim() || undefined,
      })

      setMessage(`结算已记录。${response.recalibrate}`)
      const nextCalibration = await getCalibration()
      setCalibration(nextCalibration)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '记录结算失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const runRecalibrate = async () => {
    if (isRecalibrating) {
      return
    }

    setIsRecalibrating(true)
    setMessage('')
    setError('')

    try {
      const response = await triggerRecalibrate()
      const nextCalibration = await getCalibration()
      setCalibration(nextCalibration)
      setMessage(String(response.message ?? '校准已触发'))
    } catch (recalibrateError) {
      setError(recalibrateError instanceof Error ? recalibrateError.message : '触发校准失败')
    } finally {
      setIsRecalibrating(false)
    }
  }

  if (loading) {
    return (
      <SectionCard
        title="结算历史"
        eyebrow="正在加载"
        description="页面正在读取最新结果和校准状态。"
      >
        <p className="text-sm leading-7 text-ink/80">请稍等片刻...</p>
      </SectionCard>
    )
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <SectionCard
          title="待结算队列"
          eyebrow="真实结算"
          description="当前页优先服务最近一次真实评审。团队只需要选赢家、填指标、点提交。"
        >
          {result ? (
            <div className="space-y-3">
              <div className="rounded-3xl border border-coffee bg-coffee px-4 py-4 text-paper shadow-card">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-lg font-semibold">{latest?.reviewName || result.set_id}</p>
                  <span className="inline-flex items-center rounded-full border border-paper/30 bg-paper/15 px-3 py-1 text-xs font-semibold tracking-wide text-paper">
                    待结算
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-paper/80">
                  set_id: {result.set_id}。先记录真实赢家，再看是否达到校准门槛。
                </p>
              </div>

              {result.rankings.map((item) => (
                <div key={item.campaign_id} className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-semibold text-coffee">{item.campaign_name}</p>
                    <StatusBadge
                      label={item.verdict === 'ship' ? '结果主推' : item.verdict === 'revise' ? '结果保留' : '结果淘汰'}
                      tone={item.verdict === 'ship' ? 'done' : item.verdict === 'revise' ? 'neutral' : 'warning'}
                    />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-ink/80">
                    Rank #{item.rank} · Panel {item.panel_avg.toFixed(1)} · Pairwise {item.pairwise_wins} 胜
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm leading-7 text-ink/80">
                还没有可结算的评审结果。请先完成一次真实评审。
              </p>
              <Link className="primary-button" to="/new-review">
                去新建评审
              </Link>
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="校准状态"
          eyebrow="真实后端状态"
          description={calibration?.message ?? '页面会读取后端 /calibration 接口的当前状态。'}
          action={<StatusBadge label={calibration?.calibration_ready ? '可校准' : '未达门槛'} tone={calibration?.calibration_ready ? 'done' : 'draft'} />}
        >
          <div className="space-y-3">
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
              已结算评审集：{calibration?.resolved_set_count ?? 0}
            </div>
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
              有 predictions 的评审集：{calibration?.sets_with_predictions ?? 0}
            </div>
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
              Persona calibration：{calibration?.persona_calibration ?? 'not_run'}
            </div>
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
              Judge calibration：{calibration?.judge_calibration ?? 'not_run'}
            </div>

            <button className="secondary-button w-full justify-center" type="button" onClick={runRecalibrate} disabled={isRecalibrating}>
              {isRecalibrating ? '正在触发校准...' : '手动触发 recalibrate'}
            </button>
          </div>
        </SectionCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <SectionCard
          title="结算回填"
          eyebrow="已接真实接口"
          description="这里只保留最必要字段，尽量让非技术同事也能顺着页面完成回填。"
        >
          {result ? (
            <>
              <div className="mb-5 rounded-3xl border border-line/70 bg-cream px-4 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="font-semibold text-coffee">{latest?.reviewName || result.set_id}</p>
                  <StatusBadge label="准备回填" tone="settlement" />
                </div>
                <p className="mt-2 text-sm leading-6 text-ink/80">
                  真实表现填进去之后，后端会把这次结果记入 resolution 记录，供后续校准使用。
                </p>
              </div>

              <div className="space-y-5">
                <label className="block space-y-2">
                  <span className="field-label">真实胜出方案</span>
                  <select className="field-select" value={winnerId} onChange={(event) => setWinnerId(event.target.value)}>
                    <option value="" disabled>
                      请选择实际投放后表现最好的方案
                    </option>
                    {result.rankings.map((item) => (
                      <option key={item.campaign_id} value={item.campaign_id}>
                        {item.campaign_name}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="rounded-3xl border border-line/50 bg-cream/50 px-4 py-4">
                  <p className="field-label mb-3">投放表现指标</p>
                  <div className="grid gap-4 md:grid-cols-2">
                    {metricKeys.map((key) => (
                      <label key={key} className="space-y-2">
                        <span className="text-xs text-ink/60">{result.resolution_ready_fields?.[key] ?? key}</span>
                        <input
                          className="field-input"
                          inputMode="decimal"
                          placeholder="例如 0.03"
                          value={metrics[key] ?? ''}
                          onChange={(event) => handleMetricChange(key, event.target.value)}
                        />
                      </label>
                    ))}
                  </div>
                </div>

                <label className="block space-y-2">
                  <span className="field-label">复盘说明</span>
                  <textarea
                    className="field-textarea"
                    rows={4}
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="写清楚这次结果是否支持原结论，以及后续要不要继续优化。"
                  />
                </label>
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <button className="primary-button" type="button" onClick={submitResolution} disabled={!winnerId || isSubmitting}>
                  {isSubmitting ? '正在记录结算...' : '记录结算结果'}
                </button>
                <Link className="secondary-button" to={`/result?setId=${result.set_id}`}>
                  回结果页
                </Link>
              </div>
            </>
          ) : (
            <p className="text-sm leading-7 text-ink/80">还没有可回填的真实结果。</p>
          )}

          {message ? (
            <div className="mt-5 rounded-3xl border border-mist/25 bg-mist-soft/45 px-4 py-4 text-sm leading-6 text-ink/80">
              {message}
            </div>
          ) : null}

          {error ? (
            <div className="mt-5 rounded-3xl border border-wine/20 bg-wine/10 px-4 py-4 text-sm leading-6 text-wine">
              {error}
            </div>
          ) : null}
        </SectionCard>

        <SectionCard
          title="页面说明"
          eyebrow="给团队看的"
          description="把操作门槛尽量压低，不要求大家懂 API 细节。"
        >
          <div className="space-y-3">
            <div className="rounded-3xl border border-mist/25 bg-mist-soft/40 px-4 py-4">
              <p className="font-semibold text-coffee">当前页怎么用</p>
              <p className="mt-2 text-sm leading-6 text-ink/80">
                选真实赢家，填 1 到 3 个关键指标，补一句复盘说明，然后点“记录结算结果”。
              </p>
            </div>
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4 text-sm leading-6 text-ink/80">
              当 <code>sets_with_predictions &gt;= 5</code> 时，后端就具备更可靠的校准基础。
            </div>
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4 text-sm leading-6 text-ink/80">
              如果后端返回 409，通常表示这次评审已经结算过，不需要重复提交。
            </div>
          </div>
        </SectionCard>
      </section>
    </div>
  )
}
