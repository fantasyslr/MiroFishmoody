import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { getLatestReviewSession, getTasks, type TaskListItem } from '../lib/api'
import { dashboardNotes } from '../data/campaignDecisionData'

const statusToneMap = {
  pending: 'draft',
  processing: 'running',
  completed: 'done',
  failed: 'warning',
} as const

const statusLabelMap = {
  pending: '排队中',
  processing: '运行中',
  completed: '已完成',
  failed: '失败',
} as const

export function DashboardPage() {
  const latest = getLatestReviewSession()

  const [tasks, setTasks] = useState<TaskListItem[]>([])
  const [loaded, setLoaded] = useState(false)
  const [usingApi, setUsingApi] = useState(false)

  useEffect(() => {
    let cancelled = false

    getTasks()
      .then((response) => {
        if (cancelled) return
        setTasks(response.tasks)
        setUsingApi(true)
      })
      .catch(() => {
        // backend offline — dashboard stays in example mode
      })
      .finally(() => {
        if (!cancelled) setLoaded(true)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const runningCount = tasks.filter((t) => t.status === 'processing' || t.status === 'pending').length
  const completedCount = tasks.filter((t) => t.status === 'completed').length
  const failedCount = tasks.filter((t) => t.status === 'failed').length

  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-[1.45fr,0.95fr]">
        <div className="rounded-panel border border-line bg-paper/95 p-6 shadow-paper sm:p-8">
          <p className="section-label">总览台</p>
          <h2 className="mt-3 max-w-3xl font-serif text-3xl font-semibold leading-tight text-coffee sm:text-4xl">
            一个给内部团队推进评审的前端壳，不是交易终端，也不是普通后台。
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-ink/85">
            这里的任务不是制造"平台感"，而是把当前要推进的评审、已出的结论和待回填的事项摆清楚。
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link className="primary-button" to="/new-review">
              新建评审
            </Link>
            <Link className="secondary-button" to="/history">
              去看结算 / 历史
            </Link>
          </div>

          {latest?.setId ? (
            <div className="mt-8 grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
              <div className="rounded-panel border border-line/60 bg-cream px-5 py-5">
                <p className="field-label">最近一次评审</p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <h3 className="font-serif text-2xl font-semibold text-coffee">
                    {latest.reviewName || '未命名评审'}
                  </h3>
                  <StatusBadge label="最近" tone="running" />
                </div>
                <p className="mt-3 text-sm leading-7 text-ink/80">
                  set_id: {latest.setId}
                  {latest.taskId ? ` · task_id: ${latest.taskId}` : ''}
                </p>
              </div>

              <div className="rounded-panel border border-mist/25 bg-mist-soft/40 px-5 py-5">
                <p className="field-label">快速跳转</p>
                <div className="mt-3 flex flex-col gap-2">
                  {latest.taskId ? (
                    <Link
                      className="secondary-button justify-center"
                      to={`/running?taskId=${latest.taskId}&setId=${latest.setId}`}
                    >
                      查看运行状态
                    </Link>
                  ) : null}
                  <Link
                    className="secondary-button justify-center"
                    to={`/result?setId=${latest.setId}`}
                  >
                    查看结果页
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-8 rounded-panel border border-mist/25 bg-mist-soft/40 px-5 py-5">
              <p className="field-label">还没有评审记录</p>
              <p className="mt-3 text-sm leading-7 text-ink/80">
                从新建评审页提交第一个评审任务后，这里会显示最近的评审信息。
              </p>
            </div>
          )}
        </div>

        <SectionCard
          title="本轮页面收口原则"
          eyebrow={usingApi ? '已连接后端' : '示例说明'}
          description={usingApi ? '总览台正在读取后端真实任务列表。' : '所有数字和状态都明确标注为示例，不让假数据伪装成经营真值。'}
          action={<StatusBadge label={usingApi ? '已接后端' : '示例数据'} tone={usingApi ? 'done' : 'draft'} />}
        >
          <div className="space-y-3 text-sm leading-7 text-ink/85">
            {dashboardNotes.focus.map((item) => (
              <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3">
                {item}
              </div>
            ))}
          </div>
        </SectionCard>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: '运行中',
            value: usingApi ? `${runningCount} 项` : '—',
            note: usingApi ? '当前正在排队或运行的评审任务。' : '后端未连接，无法读取真实任务状态。',
            highlight: true,
          },
          {
            label: '已完成',
            value: usingApi ? `${completedCount} 项` : '—',
            note: usingApi ? '已产出结果，下一步是查看结论或回填真实投放表现。' : '后端未连接。',
          },
          {
            label: '失败',
            value: usingApi ? `${failedCount} 项` : '—',
            note: usingApi ? '检查 LLM 配置或网络连接后重新提交。' : '后端未连接。',
          },
          {
            label: '总任务数',
            value: usingApi ? `${tasks.length} 项` : '—',
            note: usingApi ? '后端内存中保留的所有评审任务。' : '后端未连接。',
          },
        ].map((metric, index) => (
          <article
            key={metric.label}
            className="group rounded-panel border border-line/80 bg-paper/95 p-5 shadow-card transition-shadow duration-300 hover:shadow-paper"
          >
            <p className="section-label">{metric.label}</p>
            <p className={`mt-3 font-serif text-2xl font-semibold ${index === 0 && metric.highlight ? 'text-coffee' : 'text-ink/90'}`}>{metric.value}</p>
            <p className="mt-2 text-sm leading-6 text-ink/70">{metric.note}</p>
          </article>
        ))}
      </div>

      {usingApi && tasks.length > 0 ? (
        <div className="grid gap-6 xl:grid-cols-[1.55fr,0.95fr]">
          <SectionCard
            title="任务列表"
            eyebrow="真实后端数据"
            description="这些任务来自后端 /api/campaign/tasks 接口。"
            action={<StatusBadge label="已接后端" tone="done" />}
          >
            <div className="space-y-4">
              {tasks.map((task) => (
                <article
                  key={task.task_id}
                  className="rounded-3xl border border-line/70 bg-cream px-4 py-4 transition-all duration-200 hover:border-mist/60 hover:bg-paper hover:shadow-sm"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold text-coffee">
                          {(task.result as Record<string, unknown>)?.set_id
                            ? String((task.result as Record<string, unknown>).set_id)
                            : task.task_id}
                        </h3>
                        <StatusBadge label={statusLabelMap[task.status]} tone={statusToneMap[task.status]} />
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-ink/70">
                        <span className="rounded-full border border-line bg-paper px-3 py-1">
                          {task.progress}%
                        </span>
                        <span className="rounded-full border border-line bg-paper px-3 py-1">
                          {task.message || '无消息'}
                        </span>
                      </div>
                    </div>
                    {task.status === 'completed' && (task.result as Record<string, unknown>)?.set_id ? (
                      <Link
                        className="secondary-button whitespace-nowrap"
                        to={`/result?setId=${String((task.result as Record<string, unknown>).set_id)}`}
                      >
                        查看结果
                      </Link>
                    ) : task.status === 'processing' || task.status === 'pending' ? (
                      <Link
                        className="secondary-button whitespace-nowrap"
                        to={`/running?taskId=${task.task_id}`}
                      >
                        查看进度
                      </Link>
                    ) : null}
                  </div>
                  {task.error ? (
                    <p className="mt-3 text-sm leading-6 text-wine">{task.error}</p>
                  ) : null}
                </article>
              ))}
            </div>
          </SectionCard>

          <div className="space-y-6">
            <SectionCard
              title="本周重点"
              eyebrow="不是数据墙"
              description="右侧只保留短决策句，避免把页面又做回普通 SaaS 卡片拼盘。"
            >
              <div className="space-y-3">
                {dashboardNotes.workbench.map((item) => (
                  <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
                    {item}
                  </div>
                ))}
              </div>
            </SectionCard>

            <SectionCard
              title="联调提示"
              eyebrow="当前总览已接后端"
              description="如果后端重启，内存中的任务会清空，需要重新提交。"
            >
              <div className="space-y-3 text-sm leading-6 text-ink/80">
                <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3">
                  前端通过 Vite 代理把 `/api` 和 `/health` 转发到 `http://localhost:5001`。
                </div>
                <div className="rounded-3xl border border-line/70 bg-cream px-4 py-3">
                  后端 MVP 阶段使用内存存储，重启后任务列表会清空。
                </div>
              </div>
            </SectionCard>
          </div>
        </div>
      ) : loaded && !usingApi ? (
        <div className="grid gap-6 xl:grid-cols-[1.55fr,0.95fr]">
          <SectionCard
            title="后端未连接"
            eyebrow="离线模式"
            description="无法读取真实任务列表。请确认后端服务是否已启动。"
          >
            <div className="space-y-4">
              <div className="rounded-3xl border border-wine/20 bg-wine/10 px-4 py-4 text-sm leading-6 text-ink/80">
                总览台尝试连接 `/api/campaign/tasks` 失败。新建评审页仍可正常提交（提交时会直接调用后端）。
              </div>
              <div className="rounded-3xl border border-mist/25 bg-mist-soft/40 px-4 py-4 text-sm leading-6 text-ink/80">
                如果只是想查看页面样式，可以继续浏览其他页面。
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="本周重点"
            eyebrow="示例说明"
            description="右侧只保留短决策句，避免把页面又做回普通 SaaS 卡片拼盘。"
            action={<StatusBadge label="示例数据" tone="draft" />}
          >
            <div className="space-y-3">
              {dashboardNotes.workbench.map((item) => (
                <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
                  {item}
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      ) : null}
    </div>
  )
}
