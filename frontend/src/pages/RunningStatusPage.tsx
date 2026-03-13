import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import {
  getLatestReviewSession,
  getTaskStatus,
  saveLatestReviewSession,
  type TaskStatusResponse,
} from '../lib/api'

const toneMap = {
  pending: 'draft',
  processing: 'running',
  completed: 'done',
  failed: 'warning',
} as const

const stageHints = [
  '初始化评审引擎...',
  'Audience Panel 评审中...',
  'Panel 评审完成',
  'Pairwise 对决中...',
  '对决完成',
  'Market scoring...',
  '生成总结报告...',
  '任务完成',
]

export function RunningStatusPage() {
  const [searchParams] = useSearchParams()
  const latest = getLatestReviewSession()
  const taskId = searchParams.get('taskId') ?? latest?.taskId ?? ''
  const setId = searchParams.get('setId') ?? latest?.setId ?? ''

  const [task, setTask] = useState<TaskStatusResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!taskId) {
      return
    }

    let cancelled = false
    let timer: number | undefined

    const poll = async () => {
      try {
        const nextTask = await getTaskStatus(taskId)
        if (cancelled) {
          return
        }

        setTask(nextTask)
        setError('')

        const nextSetId = nextTask.result?.set_id ?? setId
        if (nextSetId) {
          saveLatestReviewSession({
            taskId,
            setId: nextSetId,
            reviewName: latest?.reviewName,
          })
        }

        if (nextTask.status === 'pending' || nextTask.status === 'processing') {
          timer = window.setTimeout(poll, 2500)
        }
      } catch (pollError) {
        if (cancelled) {
          return
        }
        setError(pollError instanceof Error ? pollError.message : '获取任务状态失败')
      }
    }

    void poll()

    return () => {
      cancelled = true
      if (timer) {
        window.clearTimeout(timer)
      }
    }
  }, [latest?.reviewName, setId, taskId])

  if (!taskId) {
    return (
      <SectionCard
        title="运行状态"
        eyebrow="还没有任务"
        description="请先到新建评审页提交一个真实评审任务。"
      >
        <div className="space-y-4">
          <p className="text-sm leading-7 text-ink/80">
            当前没有可追踪的 `taskId`。从新建评审页提交后，这里会自动显示真实进度。
          </p>
          <Link className="primary-button" to="/new-review">
            去新建评审
          </Link>
        </div>
      </SectionCard>
    )
  }

  const progress = task?.progress ?? 0
  const currentStatus = task?.status ?? 'pending'
  const currentMessage = error || task?.error || task?.message || '正在连接后端...'
  const progressWidth = `${Math.max(progress, 6)}%`
  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <div className="rounded-panel border border-line bg-paper/95 p-6 shadow-paper sm:p-8">
          <p className="section-label">运行中状态页</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h2 className="font-serif text-3xl font-semibold text-coffee">
              {latest?.reviewName || 'Campaign 评审任务'}
            </h2>
            <StatusBadge
              label={currentStatus === 'completed' ? '已完成' : currentStatus === 'failed' ? '失败' : '运行中'}
              tone={toneMap[currentStatus]}
            />
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/85">
            页面正在轮询后端任务状态。任务失败时会直接显示错误，不会把无效结果伪装成正常完成。
          </p>

          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between text-sm text-ink/80">
              <span>{task?.message || '等待任务启动'}</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-stone/70">
              <div className="relative h-full rounded-full bg-coffee transition-all duration-700" style={{ width: progressWidth }}>
                <span className="absolute right-0 top-0 h-full w-3 animate-pulse rounded-full bg-paper/30" />
              </div>
            </div>
            <p className="text-sm font-semibold text-mist">
              task_id: {taskId}
              {setId ? ` · set_id: ${setId}` : ''}
            </p>
          </div>

          <div className="mt-7 grid gap-3 md:grid-cols-3">
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="field-label">任务状态</p>
              <p className="mt-3 font-serif text-2xl font-semibold text-coffee">
                {currentStatus}
              </p>
            </div>
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="field-label">当前进度</p>
              <p className="mt-3 font-serif text-2xl font-semibold text-coffee">{progress}%</p>
            </div>
            <div className="rounded-3xl border border-mist/25 bg-mist-soft/45 px-4 py-4">
              <p className="field-label">下一动作</p>
              <p className="mt-3 text-sm leading-6 text-ink/80">
                {currentStatus === 'completed'
                  ? '进入结果页查看真实排序和建议。'
                  : currentStatus === 'failed'
                    ? '检查 LLM 配置或网络连接后重新提交。'
                    : '等待当前阶段完成，页面会自动刷新状态。'}
              </p>
            </div>
          </div>
        </div>

        <SectionCard
          title="当前阶段"
          eyebrow="团队可读"
          description="不展示后台实现细节，只告诉团队现在做到哪一步、下一步去哪看。"
        >
          <div className="space-y-3">
            <div className="rounded-3xl border border-mist/25 bg-mist-soft/50 px-4 py-4">
              <p className="font-semibold text-coffee">{task?.message || '等待任务启动'}</p>
              <p className="mt-2 text-sm leading-6 text-ink/80">{currentMessage}</p>
            </div>

            <div className="flex flex-col gap-3">
              {currentStatus === 'completed' && setId ? (
                <Link className="primary-button w-full justify-center" to={`/result?setId=${setId}`}>
                  查看真实结果页
                </Link>
              ) : null}
              <Link className="secondary-button w-full justify-center" to="/new-review">
                返回新建评审
              </Link>
            </div>
          </div>
        </SectionCard>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <SectionCard
          title="阶段进度"
          eyebrow="真实轮询"
          description="阶段名来自后端任务消息，下面这条时间线只帮助团队理解“当前在哪一步”。"
        >
          <div className="space-y-0">
            {stageHints.map((stage, index) => {
              const currentIndex = stageHints.indexOf(task?.message ?? '')
              const status =
                currentStatus === 'failed'
                  ? index < Math.max(currentIndex, 0)
                    ? 'done'
                    : index === Math.max(currentIndex, 0)
                      ? 'current'
                      : 'upcoming'
                  : index < currentIndex
                    ? 'done'
                    : index === currentIndex
                      ? 'current'
                      : 'upcoming'

              return (
                <div key={stage} className="relative flex gap-5 pb-5 last:pb-0">
                  {index < stageHints.length - 1 ? (
                    <div className="absolute left-[15px] top-9 h-[calc(100%-20px)] w-px bg-line/60" />
                  ) : null}
                  <div className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${
                    status === 'current'
                      ? 'border-mist/50 bg-mist-soft text-coffee shadow-sm'
                      : status === 'done'
                        ? 'border-line/50 bg-stone/60 text-ink/50'
                        : 'border-line/70 bg-cream text-coffee'
                  }`}>
                    {index + 1}
                  </div>

                  <div className={`flex-1 rounded-3xl border px-4 py-4 transition-all duration-200 ${
                    status === 'current'
                      ? 'border-mist/40 bg-mist-soft/30 shadow-sm'
                      : status === 'done'
                        ? 'border-line/50 bg-cream/70'
                        : 'border-line/70 bg-cream'
                  }`}>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className={`font-semibold ${status === 'done' ? 'text-ink/60' : 'text-coffee'}`}>{stage}</p>
                      <StatusBadge
                        label={status === 'done' ? '已过' : status === 'current' ? '当前' : '待开始'}
                        tone={status === 'done' ? 'done' : status === 'current' ? 'running' : 'draft'}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard
            title="结果速记"
            eyebrow="任务完成后可直接读"
            description="完成后这里会展示后端返回的核心摘要，方便非技术同事先看一眼。"
          >
            <div className="space-y-3">
              <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                <p className="font-semibold text-coffee">候选主推方案</p>
                <p className="mt-2 text-sm leading-6 text-ink/80">
                  {task?.result?.top_campaign ?? '尚未产出'}
                </p>
              </div>
              <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                <p className="font-semibold text-coffee">判定</p>
                <p className="mt-2 text-sm leading-6 text-ink/80">
                  {task?.result?.top_verdict ?? '尚未产出'}
                </p>
              </div>
              <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                <p className="font-semibold text-coffee">领先幅度</p>
                <p className="mt-2 text-sm leading-6 text-ink/80">
                  {task?.result?.spread !== undefined ? `${Math.round(task.result.spread * 100)}%` : '尚未产出'}
                </p>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="联调提示"
            eyebrow="当前这页已接后端"
            description="如果任务失败，优先检查后端服务、LLM 配置和网络连接。"
          >
            <div className="space-y-3 text-sm leading-6 text-ink/80">
              <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3">
                前端通过 Vite 代理把 `/api` 和 `/health` 转发到 `http://localhost:5001`。
              </div>
              <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3">
                如果没有 `.env` 或 `LLM_API_KEY` 不正确，后端任务会进入 failed，而不是给出假结果。
              </div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
