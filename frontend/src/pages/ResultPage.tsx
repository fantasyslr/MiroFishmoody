import { Link } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { resultReview } from '../data/campaignDecisionData'

function LevelMeter({ level }: { level: 1 | 2 | 3 }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3].map((item) => (
        <span
          key={item}
          className={`h-2.5 w-8 rounded-full ${item <= level ? 'bg-coffee' : 'bg-stone'}`}
        />
      ))}
    </div>
  )
}

export function ResultPage() {
  return (
    <div className="space-y-6">
      <section className="rounded-panel border border-line bg-paper/95 p-6 shadow-paper sm:p-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="section-label">结果页</p>
              <StatusBadge label={resultReview.badge} tone="draft" />
            </div>
            <h2 className="mt-3 font-serif text-3xl font-semibold text-coffee sm:text-4xl">
              {resultReview.recommendation.title}
            </h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/85">
              {resultReview.recommendation.summary}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button className="primary-button" type="button">
              标记为优先测试
            </button>
            <button className="secondary-button" type="button">
              进入下一轮优化
            </button>
            <Link className="secondary-button" to="/history">
              去做结算
            </Link>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <SectionCard
          title="方案排序"
          eyebrow="不伪造高精度"
          description="不用假百分比，用相对强弱和执行价值来表达排序。"
        >
          <div className="space-y-4">
            {resultReview.rankings.map((ranking) => (
              <article key={ranking.rank} className="rounded-panel border border-line/80 bg-cream px-4 py-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-serif text-2xl font-semibold text-coffee">{ranking.rank}</span>
                      <div>
                        <p className="text-lg font-semibold text-coffee">{ranking.name}</p>
                        <p className="mt-1 text-sm leading-6 text-ink/80">{ranking.summary}</p>
                      </div>
                    </div>
                  </div>
                  <StatusBadge label={ranking.statusLabel} tone={ranking.statusTone} />
                </div>

                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  <div className="rounded-3xl border border-line/70 bg-paper px-4 py-3">
                    <p className="field-label">值得保留</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {ranking.strengths.map((item) => (
                        <span key={item} className="tag-chip">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-3xl border border-line/70 bg-paper px-4 py-3">
                    <p className="field-label">需要注意</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {ranking.concerns.map((item) => (
                        <span key={item} className="tag-chip tag-chip-warning">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="系统摘要"
          eyebrow="一句话先告诉团队怎么做"
          description="结果页最重要的是动作建议，而不是展示一个华丽的分析框架。"
        >
          <div className="space-y-4">
            <div className="rounded-3xl border border-mist/25 bg-mist-soft/45 px-4 py-4">
              <p className="font-semibold text-coffee">结论摘要</p>
              <p className="mt-2 text-sm leading-7 text-ink/80">{resultReview.summary}</p>
            </div>

            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="font-semibold text-coffee">假设前提</p>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-ink/80">
                {resultReview.assumptions.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>

            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="font-semibold text-coffee">置信提醒</p>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-ink/80">
                {resultReview.confidenceNotes.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <SectionCard
          title="维度差异"
          eyebrow="相对强弱"
          description="这里用定性等级代替伪精度数字，仍然保留对比价值。"
        >
          <div className="space-y-3">
            {resultReview.matrix.map((row) => (
              <div key={row.label} className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                <div className="border-b border-line/70 pb-3">
                  <p className="font-semibold text-coffee">{row.label}</p>
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                  {row.values.map((item) => (
                    <div key={`${row.label}-${item.campaign}`} className="rounded-3xl border border-line/60 bg-paper px-4 py-3">
                      <p className="text-sm font-semibold text-coffee">{item.campaign}</p>
                      <div className="mt-3">
                        <LevelMeter level={item.level} />
                      </div>
                      <p className="mt-3 text-sm leading-6 text-ink/80">{item.note}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard
            title="受众反馈摘要"
            eyebrow="看人话，不看术语"
            description="把最关键的阅读感受留在结果页里，让团队能直接用。"
          >
            <div className="space-y-3">
              {resultReview.audienceTakeaways.map((item) => (
                <div key={item.title} className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                  <p className="font-semibold text-coffee">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-ink/80">{item.note}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            title="两两比较摘要"
            eyebrow="收成短句"
            description="只保留能解释排序的差异，不堆复杂结构。"
          >
            <div className="space-y-3">
              {resultReview.pairwiseNotes.map((item) => (
                <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
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
