import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'motion/react'
import { Download, CheckCircle2, AlertCircle, XCircle } from 'lucide-react'
import { cn } from '../utils'
import { useReviewStore } from '../store'
import {
  campaignImageUrl,
  exportResult,
  getLatestReviewSession,
  getResult,
  saveLatestReviewSession,
  type EvaluationResult,
  type Ranking,
} from '../lib/api'

const verdictConfig = {
  ship: {
    label: '建议上线',
    color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    Icon: CheckCircle2,
  },
  revise: {
    label: '建议优化',
    color: 'text-amber-600 bg-amber-50 border-amber-200',
    Icon: AlertCircle,
  },
  kill: {
    label: '建议放弃',
    color: 'text-rose-600 bg-rose-50 border-rose-200',
    Icon: XCircle,
  },
} as const

function VerdictBadge({ verdict }: { verdict: Ranking['verdict'] }) {
  const config = verdictConfig[verdict]
  const Icon = config.Icon
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium',
        config.color,
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {config.label}
    </span>
  )
}

export function ResultPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const latest = getLatestReviewSession()
  const setId = searchParams.get('setId') ?? latest?.setId ?? ''

  const [result, setResultData] = useState<EvaluationResult | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(Boolean(setId))
  const reset = useReviewStore((s) => s.reset)

  useEffect(() => {
    if (!setId) return

    let cancelled = false
    const load = async () => {
      try {
        setLoading(true)
        const data = await getResult(setId)
        if (cancelled) return
        setResultData(data)
        saveLatestReviewSession({
          taskId: latest?.taskId,
          setId,
          reviewName: latest?.reviewName,
        })
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : '加载结果失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [setId, latest?.taskId, latest?.reviewName])

  const handleNewReview = () => {
    reset()
    navigate('/')
  }

  const handleExport = () => {
    void exportResult(setId).catch((err) => {
      alert(err instanceof Error ? err.message : '导出失败')
    })
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-stone-500">正在加载结果...</p>
      </div>
    )
  }

  if (error || !result) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
        <p className="text-stone-500">{error || '没有可用的评审结果'}</p>
        <button onClick={() => navigate('/')} className="text-stone-900 underline">
          返回首页
        </button>
      </div>
    )
  }

  const winner = result.rankings[0]

  /** Per-campaign image URLs */
  const getImageUrls = (campaignId: string): string[] => {
    const map = result.campaign_image_map
    if (!map) return []
    return map[campaignId] ?? map._all ?? []
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="pb-24">
      {/* Conclusion header */}
      <div className="mb-12">
        <h1 className="mb-4 text-2xl font-semibold leading-snug tracking-tight">
          {result.summary}
        </h1>
        {winner && (
          <div className="flex items-center gap-3">
            <span className="text-stone-500">推荐方案：</span>
            <span className="font-medium">{winner.campaign_name}</span>
            <VerdictBadge verdict={winner.verdict} />
          </div>
        )}
      </div>

      {/* Ranking cards */}
      <div className="space-y-6">
        {result.rankings.map((ranking) => {
          const images = getImageUrls(ranking.campaign_id)
          return (
            <div
              key={ranking.campaign_id}
              className="flex flex-col gap-6 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm md:flex-row"
            >
              <div className="flex flex-shrink-0 items-start gap-4 md:w-1/3">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-stone-200 bg-stone-100 font-semibold text-stone-900">
                  {ranking.rank}
                </div>
                <div>
                  <h3 className="mb-2 text-lg font-semibold">{ranking.campaign_name}</h3>
                  <VerdictBadge verdict={ranking.verdict} />
                  {images.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {images.map((url) => (
                        <a
                          key={url}
                          href={campaignImageUrl(url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block h-12 w-12 overflow-hidden rounded-md border border-stone-200"
                        >
                          <img
                            src={campaignImageUrl(url)}
                            alt=""
                            className="h-full w-full object-cover"
                            loading="lazy"
                          />
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="grid flex-1 grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-stone-400">
                    值得保留
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {ranking.top_strengths.length > 0 ? (
                      ranking.top_strengths.map((item) => (
                        <span
                          key={item}
                          className="rounded-md border border-stone-200/60 bg-stone-100 px-2.5 py-1 text-xs text-stone-700"
                        >
                          {item}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-stone-400">暂无</span>
                    )}
                  </div>
                </div>
                <div>
                  <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-stone-400">
                    需要注意
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {ranking.top_objections.length > 0 ? (
                      ranking.top_objections.map((item) => (
                        <span
                          key={item}
                          className="rounded-md border border-orange-100 bg-orange-50 px-2.5 py-1 text-xs text-orange-800"
                        >
                          {item}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-stone-400">暂无</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Bottom actions */}
      <div className="pointer-events-none fixed bottom-0 left-0 right-0 z-20 flex justify-center bg-gradient-to-t from-[#FDFCFB] via-[#FDFCFB] to-transparent p-6">
        <div className="pointer-events-auto flex w-full max-w-2xl gap-4">
          <button
            onClick={handleExport}
            className="flex flex-1 items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white py-4 text-base font-medium text-stone-700 shadow-sm transition-all hover:bg-stone-50"
          >
            <Download className="h-4 w-4" />
            导出报告
          </button>
          <button
            onClick={handleNewReview}
            className="flex flex-[2] items-center justify-center gap-2 rounded-2xl bg-stone-900 py-4 text-base font-medium text-white shadow-xl shadow-stone-900/10 transition-all hover:bg-stone-800"
          >
            发起新评审
          </button>
        </div>
      </div>
    </motion.div>
  )
}
