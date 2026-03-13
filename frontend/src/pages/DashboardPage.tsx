import { Link } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { dashboardMetrics, dashboardNotes, dashboardReviews } from '../data/campaignDecisionData'

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[1.45fr,0.95fr]">
        <div className="rounded-panel border border-line bg-paper/95 p-6 shadow-paper sm:p-8">
          <p className="section-label">总览台</p>
          <h2 className="mt-3 max-w-3xl font-serif text-3xl font-semibold leading-tight text-coffee sm:text-4xl">
            一个给内部团队推进评审的前端壳，不是交易终端，也不是普通后台。
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-ink/85">
            这里的任务不是制造“平台感”，而是把当前要推进的评审、已出的结论和待回填的事项摆清楚。
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link className="primary-button" to="/new-review">
              新建评审
            </Link>
            <Link className="secondary-button" to="/history">
              去看结算 / 历史
            </Link>
          </div>
        </div>

        <SectionCard
          title="本轮页面收口原则"
          eyebrow="示例说明"
          description="所有数字和状态都明确标注为示例，不让假数据伪装成经营真值。"
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
        {dashboardMetrics.map((metric) => (
          <article
            key={metric.label}
            className="rounded-panel border border-line/80 bg-paper/95 p-5 shadow-card"
          >
            <p className="section-label">{metric.label}</p>
            <p className="mt-3 font-serif text-2xl font-semibold text-coffee">{metric.value}</p>
            <p className="mt-2 text-sm leading-6 text-ink/80">{metric.note}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.55fr,0.95fr]">
        <SectionCard
          title="当前工作队列"
          eyebrow="今天先处理什么"
          description="总览台只保留对团队有动作意义的评审，不再展示装饰性指标。"
          action={<StatusBadge label="示例数据" tone="draft" />}
        >
          <div className="space-y-4">
            {dashboardReviews.map((review) => (
              <article
                key={review.title}
                className="rounded-3xl border border-line/70 bg-cream px-4 py-4 transition hover:border-mist hover:bg-paper"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold text-coffee">{review.title}</h3>
                      <StatusBadge label={review.statusLabel} tone={review.statusTone} />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-ink/70">
                      <span className="rounded-full border border-line bg-paper px-3 py-1">
                        {review.productLine}
                      </span>
                      <span className="rounded-full border border-line bg-paper px-3 py-1">
                        {review.stage}
                      </span>
                    </div>
                  </div>
                  <Link className="secondary-button whitespace-nowrap" to="/running">
                    查看详情
                  </Link>
                </div>
                <p className="mt-4 text-sm leading-6 text-ink/80">{review.note}</p>
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
            title="待处理事项"
            eyebrow="向执行团队说人话"
            description="强调状态和下一步动作，而不是强调系统工程过程。"
          >
            <div className="space-y-4">
              <div className="rounded-3xl border border-wine/20 bg-wine/10 px-4 py-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-coffee">待结算评审</p>
                    <p className="mt-1 text-sm leading-6 text-ink/80">
                      结果已经出来，下一步不是继续分析，而是回填真实测试结果。
                    </p>
                  </div>
                  <StatusBadge label="优先处理" tone="warning" />
                </div>
              </div>

              <div className="rounded-3xl border border-mist/25 bg-mist-soft/50 px-4 py-4">
                <p className="font-semibold text-coffee">待补信息评审</p>
                <p className="mt-1 text-sm leading-6 text-ink/80">
                  claim 支撑不够、方案差异不清时，优先回到新建页补信息，不要假装已经可以评。
                </p>
              </div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
