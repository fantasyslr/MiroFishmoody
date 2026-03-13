import { Link } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { runningReview } from '../data/campaignDecisionData'

const stageTone = {
  done: 'done',
  current: 'running',
  upcoming: 'draft',
} as const

export function RunningStatusPage() {
  const completedCount = runningReview.stages.filter((stage) => stage.status === 'done').length
  const progressWidth = `${((completedCount + 0.6) / runningReview.stages.length) * 100}%`

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <div className="rounded-panel border border-line bg-paper/95 p-6 shadow-paper sm:p-8">
          <p className="section-label">运行中状态页</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h2 className="font-serif text-3xl font-semibold text-coffee">{runningReview.title}</h2>
            <StatusBadge label="示例流程" tone="draft" />
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/85">{runningReview.stageSummary}</p>

          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between text-sm text-ink/80">
              <span>{runningReview.progressLabel}</span>
              <span>{runningReview.eta}</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-stone">
              <div className="h-full rounded-full bg-coffee transition-all duration-700" style={{ width: progressWidth }} />
            </div>
            <p className="text-sm font-semibold text-mist">{runningReview.currentCampaign}</p>
          </div>
        </div>

        <SectionCard
          title="当前阶段"
          eyebrow="团队可读"
          description="不展示技术细节，直接告诉团队现在做到哪一步。"
        >
          <div className="space-y-3">
            <div className="rounded-3xl border border-mist/25 bg-mist-soft/50 px-4 py-4">
              <p className="font-semibold text-coffee">{runningReview.currentStage}</p>
              <p className="mt-2 text-sm leading-6 text-ink/80">
                当前主要在把已经收出的差异，整理成结果页可直接阅读的建议摘要。
              </p>
            </div>

            <Link className="secondary-button w-full justify-center" to="/result">
              预览结果页
            </Link>
          </div>
        </SectionCard>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <SectionCard
          title="阶段进度"
          eyebrow="只看过程，不看炫技"
          description="页面应该帮助团队理解正在发生什么，而不是展示复杂内部状态。"
        >
          <div className="space-y-4">
            {runningReview.stages.map((stage, index) => (
              <div key={stage.title} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <StatusBadge
                    label={`${index + 1}`}
                    tone={stageTone[stage.status]}
                  />
                  {index < runningReview.stages.length - 1 ? (
                    <div className="mt-2 h-full w-px bg-line" />
                  ) : null}
                </div>

                <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-coffee">{stage.title}</p>
                    <StatusBadge
                      label={
                        stage.status === 'done'
                          ? '已完成'
                          : stage.status === 'current'
                            ? '进行中'
                            : '待开始'
                      }
                      tone={stageTone[stage.status]}
                    />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-ink/80">{stage.note}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard
            title="当前方案观察"
            eyebrow="正在看的差异"
            description="这里展示的是团队需要理解的方案状态，而不是后台日志。"
          >
            <div className="space-y-3">
              {runningReview.campaignSignals.map((item) => (
                <div key={item.name} className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-coffee">{item.name}</p>
                    <StatusBadge
                      label={item.position}
                      tone={item.position === '主推' ? 'done' : item.position === '谨慎' ? 'warning' : 'neutral'}
                    />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-ink/80">{item.note}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            title="当前页应该传达什么"
            eyebrow="运行中页面的边界"
            description="这是页面的信息边界，不是给用户看的注释。"
          >
            <div className="space-y-3 text-sm leading-6 text-ink/80">
              {runningReview.highlights.map((item) => (
                <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3">
                  {item}
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
