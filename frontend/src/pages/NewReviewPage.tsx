import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { initialCampaignDrafts, reviewPreset, type CampaignDraft } from '../data/campaignDecisionData'

const emptyDraft = (index: number): CampaignDraft => ({
  id: `campaign-new-${index}`,
  name: '',
  productLine: 'moodyplus',
  targetAudience: '',
  coreMessage: '',
  channels: '',
  creativeDirection: '',
  budgetRange: '',
  kvDescription: '',
  promoMechanic: '',
})

export function NewReviewPage() {
  const navigate = useNavigate()
  const [reviewName, setReviewName] = useState(reviewPreset.reviewName)
  const [context, setContext] = useState(reviewPreset.context)
  const [campaigns, setCampaigns] = useState(initialCampaignDrafts)

  const updateCampaign = (
    index: number,
    field: keyof CampaignDraft,
    value: CampaignDraft[keyof CampaignDraft],
  ) => {
    setCampaigns((current) =>
      current.map((campaign, currentIndex) =>
        currentIndex === index ? { ...campaign, [field]: value } : campaign,
      ),
    )
  }

  const addCampaign = () => {
    setCampaigns((current) => [...current, emptyDraft(current.length + 1)])
  }

  const removeCampaign = (index: number) => {
    setCampaigns((current) => current.filter((_, currentIndex) => currentIndex !== index))
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1.45fr,0.95fr]">
        <SectionCard
          title="新建评审"
          eyebrow="先把输入写清楚"
          description="页面先解决“信息是否完整”，再讨论是否发起评审。没有背景、没有方案差异的评审只会制造噪音。"
          action={<StatusBadge label="前端示例" tone="draft" />}
        >
          <div className="grid gap-5 md:grid-cols-2">
            <label className="space-y-2 md:col-span-2">
              <span className="field-label">评审名称</span>
              <input
                className="field-input"
                value={reviewName}
                onChange={(event) => setReviewName(event.target.value)}
                placeholder="例如：moodyPlus 夏季舒适感方向评审"
              />
            </label>

            <label className="space-y-2 md:col-span-2">
              <span className="field-label">业务背景</span>
              <textarea
                className="field-textarea"
                rows={5}
                value={context}
                onChange={(event) => setContext(event.target.value)}
                placeholder="写清楚这轮评审是为哪个场景服务，以及团队真正要做的决定。"
              />
            </label>
          </div>
        </SectionCard>

        <SectionCard
          title="提交前清单"
          eyebrow="不要把问题带进结果页"
          description="这些检查比再多一个漂亮图表更重要。"
        >
          <div className="space-y-3">
            {reviewPreset.checklist.map((item) => (
              <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
                {item}
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-3xl border border-mist/25 bg-mist-soft/40 px-4 py-4">
            <p className="font-semibold text-coffee">当前页的真正职责</p>
            <p className="mt-2 text-sm leading-6 text-ink/80">
              把方案写成“可以比较”的输入，而不是只写一堆看起来高级但没法评的抽象词。
            </p>
          </div>
        </SectionCard>
      </section>

      <SectionCard
        title="方案录入"
        eyebrow="2 到 4 个方案最合适"
        description="每个方案必须有清楚的受众、主信息、渠道与创意方向。这里不做后端提交，只把前端结构落稳。"
        action={
          <button className="secondary-button" type="button" onClick={addCampaign}>
            新增方案
          </button>
        }
      >
        <div className="space-y-5">
          {campaigns.map((campaign, index) => (
            <article key={campaign.id} className="rounded-panel border border-line/80 bg-cream px-4 py-4 sm:px-5">
              <div className="mb-4 flex flex-col gap-3 border-b border-line/70 pb-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="section-label">方案 {index + 1}</p>
                  <input
                    className="mt-2 w-full border-none bg-transparent p-0 font-serif text-2xl font-semibold text-coffee placeholder:text-ink/40 focus:outline-none"
                    value={campaign.name}
                    onChange={(event) => updateCampaign(index, 'name', event.target.value)}
                    placeholder="请输入方案名"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <select
                    className="field-select"
                    value={campaign.productLine}
                    onChange={(event) =>
                      updateCampaign(
                        index,
                        'productLine',
                        event.target.value as CampaignDraft['productLine'],
                      )
                    }
                  >
                    <option value="moodyplus">moodyPlus</option>
                    <option value="colored_lenses">colored lenses</option>
                  </select>
                  {campaigns.length > 2 ? (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => removeCampaign(index)}
                    >
                      删除
                    </button>
                  ) : null}
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <label className="space-y-2">
                  <span className="field-label">目标受众</span>
                  <textarea
                    className="field-textarea"
                    rows={3}
                    value={campaign.targetAudience}
                    onChange={(event) => updateCampaign(index, 'targetAudience', event.target.value)}
                  />
                </label>

                <label className="space-y-2">
                  <span className="field-label">核心信息</span>
                  <textarea
                    className="field-textarea"
                    rows={3}
                    value={campaign.coreMessage}
                    onChange={(event) => updateCampaign(index, 'coreMessage', event.target.value)}
                  />
                </label>

                <label className="space-y-2">
                  <span className="field-label">渠道重点</span>
                  <input
                    className="field-input"
                    value={campaign.channels}
                    onChange={(event) => updateCampaign(index, 'channels', event.target.value)}
                  />
                </label>

                <label className="space-y-2">
                  <span className="field-label">创意方向</span>
                  <input
                    className="field-input"
                    value={campaign.creativeDirection}
                    onChange={(event) => updateCampaign(index, 'creativeDirection', event.target.value)}
                  />
                </label>

                <label className="space-y-2">
                  <span className="field-label">预算范围</span>
                  <input
                    className="field-input"
                    value={campaign.budgetRange}
                    onChange={(event) => updateCampaign(index, 'budgetRange', event.target.value)}
                    placeholder="建议写成范围或待确认"
                  />
                </label>

                <label className="space-y-2">
                  <span className="field-label">促销机制</span>
                  <input
                    className="field-input"
                    value={campaign.promoMechanic}
                    onChange={(event) => updateCampaign(index, 'promoMechanic', event.target.value)}
                    placeholder="可留空"
                  />
                </label>

                <label className="space-y-2 lg:col-span-2">
                  <span className="field-label">KV 描述</span>
                  <textarea
                    className="field-textarea"
                    rows={3}
                    value={campaign.kvDescription}
                    onChange={(event) => updateCampaign(index, 'kvDescription', event.target.value)}
                  />
                </label>
              </div>
            </article>
          ))}
        </div>
      </SectionCard>

      <section className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <SectionCard
          title="页面侧注"
          eyebrow="收住文案，不要飘"
          description="这些是当前稿件最容易失控的地方。"
        >
          <div className="space-y-3">
            {reviewPreset.sideNotes.map((item) => (
              <div key={item} className="rounded-3xl border border-line/70 bg-cream px-4 py-3 text-sm leading-6 text-ink/80">
                {item}
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="提交摘要"
          eyebrow="前端示例模式"
          description="当前按钮仅用于切换到运行中页面，后续可以再接真实 API。"
        >
          <div className="space-y-4">
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="font-semibold text-coffee">{reviewName || '未命名评审'}</p>
              <p className="mt-2 text-sm leading-6 text-ink/80">
                当前共录入 {campaigns.length} 个方案。提交前请确认：每个方案都真的能看出差异。
              </p>
            </div>

            <button className="primary-button w-full justify-center" type="button" onClick={() => navigate('/running')}>
              进入运行中状态页
            </button>
          </div>
        </SectionCard>
      </section>
    </div>
  )
}
