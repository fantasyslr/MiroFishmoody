import { useState } from 'react'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { calibrationState, historyRecords, settlementQueue } from '../data/campaignDecisionData'

export function HistoryPage() {
  const [selectedId, setSelectedId] = useState(settlementQueue[0]?.id ?? '')

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <SectionCard
          title="待结算队列"
          eyebrow="先回填，再谈校准"
          description="结算页的任务是把真实结果接回来，而不是继续重复结果页里的判断。"
        >
          <div className="space-y-3">
            {settlementQueue.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedId(item.id)}
                className={`w-full rounded-3xl border px-4 py-4 text-left transition ${
                  selectedId === item.id
                    ? 'border-coffee bg-coffee text-paper'
                    : 'border-line/70 bg-cream hover:border-mist'
                }`}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-lg font-semibold">{item.title}</p>
                    <p className={`mt-2 text-sm leading-6 ${selectedId === item.id ? 'text-paper/80' : 'text-ink/80'}`}>
                      {item.note}
                    </p>
                  </div>
                  <StatusBadge label={item.statusLabel} tone={item.statusTone} />
                </div>
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="校准状态"
          eyebrow="不伪造准确率"
          description={calibrationState.description}
          action={<StatusBadge label="流程说明" tone="draft" />}
        >
          <div className="space-y-3">
            {calibrationState.points.map((item) => (
              <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
                {item}
              </div>
            ))}
          </div>
        </SectionCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <SectionCard
          title="结算回填"
          eyebrow="当前是前端占位态"
          description="字段已经按实际操作习惯摆好，后续可直接接真实回填接口。"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 md:col-span-2">
              <span className="field-label">真实胜出方案</span>
              <select className="field-select" defaultValue="">
                <option value="" disabled>
                  请选择实际投放后表现最好的方案
                </option>
                <option value="campaign-a">方案 A · 轻氧专业感</option>
                <option value="campaign-b">方案 B · 通勤生活方式</option>
                <option value="campaign-c">方案 C · 老用户换购唤回</option>
              </select>
            </label>

            <label className="space-y-2">
              <span className="field-label">点击率</span>
              <input className="field-input" placeholder="待实际投放回填" />
            </label>

            <label className="space-y-2">
              <span className="field-label">转化率</span>
              <input className="field-input" placeholder="待实际投放回填" />
            </label>

            <label className="space-y-2">
              <span className="field-label">补充指标</span>
              <input className="field-input" placeholder="如收藏率、加购率等" />
            </label>

            <label className="space-y-2">
              <span className="field-label">备注</span>
              <input className="field-input" placeholder="记录特殊环境或异常情况" />
            </label>

            <label className="space-y-2 md:col-span-2">
              <span className="field-label">复盘说明</span>
              <textarea
                className="field-textarea"
                rows={4}
                placeholder="写清楚这次结果是否支持原结论，以及后续要不要继续优化。"
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button className="primary-button" type="button">
              记录结算结果
            </button>
            <button className="secondary-button" type="button">
              暂存占位
            </button>
          </div>
        </SectionCard>

        <SectionCard
          title="历史记录"
          eyebrow="回看不是回锅"
          description="历史页只保留对下一轮有帮助的状态，不堆陈旧细节。"
        >
          <div className="space-y-3">
            {historyRecords.map((item) => (
              <div key={item.title} className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="font-semibold text-coffee">{item.title}</p>
                  <StatusBadge label={item.statusLabel} tone={item.statusTone} />
                </div>
                <p className="mt-2 text-sm leading-6 text-ink/80">{item.detail}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </section>
    </div>
  )
}
