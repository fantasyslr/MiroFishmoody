import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  getLatestReviewSession,
  getTaskStatus,
  saveLatestReviewSession,
  type TaskStatusResponse,
} from '../lib/api'

export function RunningPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const latest = getLatestReviewSession()
  const taskId = searchParams.get('taskId') ?? latest?.taskId ?? ''
  const setId = searchParams.get('setId') ?? latest?.setId ?? ''

  const [task, setTask] = useState<TaskStatusResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!taskId) {
      navigate('/')
      return
    }

    let cancelled = false
    let timer: number | undefined

    const poll = async () => {
      try {
        const next = await getTaskStatus(taskId)
        if (cancelled) return

        setTask(next)
        setError('')

        const nextSetId = next.result?.set_id ?? setId
        if (nextSetId) {
          saveLatestReviewSession({
            taskId,
            setId: nextSetId,
            reviewName: latest?.reviewName,
          })
        }

        if (next.status === 'completed' && nextSetId) {
          // Small delay so user sees 100%
          setTimeout(() => {
            if (!cancelled) navigate(`/result?setId=${nextSetId}`)
          }, 800)
          return
        }

        if (next.status === 'failed') {
          setError(next.error ?? '评审任务失败')
          return
        }

        // Keep polling
        timer = window.setTimeout(poll, 2500)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : '获取任务状态失败')
        // Retry after a longer delay
        timer = window.setTimeout(poll, 5000)
      }
    }

    void poll()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [taskId, setId, navigate, latest?.reviewName])

  const progress = task?.progress ?? 0
  const stageText = task?.message ?? '正在连接...'

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#FDFCFB] p-6 font-sans text-stone-900">
      <div className="flex w-full max-w-md flex-1 flex-col items-center justify-center text-center">
        {/* Pulsing ring animation */}
        <div className="relative mb-12 flex h-32 w-32 items-center justify-center">
          <motion.div
            animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute inset-0 rounded-full border border-stone-300"
          />
          <motion.div
            animate={{ scale: [1, 1.2, 1], opacity: [0.8, 0.2, 0.8] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
            className="absolute inset-4 rounded-full border border-stone-400"
          />
          <div className="h-3 w-3 rounded-full bg-stone-900" />
        </div>

        <motion.div
          key={stageText}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-3 text-lg font-medium tracking-tight"
        >
          {stageText}
        </motion.div>

        <div className="font-mono text-sm text-stone-400">{progress}%</div>

        {error && (
          <div className="mt-8 w-full rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
            {error}
            <button
              onClick={() => navigate('/')}
              className="mt-2 block text-sm font-medium text-stone-900 underline"
            >
              返回首页
            </button>
          </div>
        )}
      </div>

      <div className="pb-8 text-xs text-stone-400">通常需要 1-2 分钟</div>
    </div>
  )
}
