import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import {
  evaluateCampaigns,
  saveLatestReviewSession,
  type CampaignInput,
} from '../lib/api'
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

function splitChannels(value: string) {
  return value
    .split(/[,\n，、/]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function toPayloadCampaign(campaign: CampaignDraft): CampaignInput {
  return {
    id: campaign.id.trim(),
    name: campaign.name.trim(),
    product_line: campaign.productLine,
    target_audience: campaign.targetAudience.trim(),
    core_message: campaign.coreMessage.trim(),
    channels: splitChannels(campaign.channels),
    creative_direction: campaign.creativeDirection.trim(),
    budget_range: campaign.budgetRange.trim() || undefined,
    kv_description: campaign.kvDescription.trim() || undefined,
    promo_mechanic: campaign.promoMechanic.trim() || undefined,
  }
}

export function NewReviewPage() {
  const navigate = useNavigate()
  const [reviewName, setReviewName] = useState(reviewPreset.reviewName)
  const [context, setContext] = useState(reviewPreset.context)
  const [campaigns, setCampaigns] = useState(initialCampaignDrafts)
  const [submitError, setSubmitError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const campaignsWithEnoughInput = campaigns.filter(
    (campaign) =>
      campaign.name.trim() &&
      campaign.targetAudience.trim() &&
      campaign.coreMessage.trim() &&
      campaign.creativeDirection.trim(),
  ).length
  const canSubmit = campaigns.length >= 2 && campaignsWithEnoughInput === campaigns.length

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

  const submitReview = async () => {
    if (!canSubmit || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setSubmitError('')

    try {
      const payload = {
        context: [reviewName.trim(), context.trim()].filter(Boolean).join('\n\n'),
        campaigns: campaigns.map(toPayloadCampaign),
      }
      const response = await evaluateCampaigns(payload)

      saveLatestReviewSession({
        taskId: response.task_id,
        setId: response.set_id,
        reviewName: reviewName.trim(),
      })

      navigate(`/running?taskId=${response.task_id}&setId=${response.set_id}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : '提交失败，请稍后再试'
      setSubmitError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-[1.45fr,0.95fr]">
        <SectionCard
          title="新建评审"
          eyebrow="先把输入写清楚"
          description="页面会直接提交到后端评审接口。没有背景、没有方案差异的评审只会制造噪音。"
          action={<StatusBadge label="已接后端" tone="done" />}
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

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="field-label">当前方案数</p>
              <p className="mt-3 font-serif text-2xl font-semibold text-coffee">
                {campaigns.length}
              </p>
              <p className="mt-2 text-sm leading-6 text-ink/80">保持在 2 到 4 个之间最适合比较。</p>
            </div>
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="field-label">输入较完整</p>
              <p className="mt-3 font-serif text-2xl font-semibold text-coffee">
                {campaignsWithEnoughInput} / {campaigns.length}
              </p>
              <p className="mt-2 text-sm leading-6 text-ink/80">至少具备名称、受众、核心信息和创意方向。</p>
            </div>
            <div className="rounded-3xl border border-mist/25 bg-mist-soft/40 px-4 py-4">
              <p className="field-label">提交模式</p>
              <p className="mt-3 text-sm leading-6 text-ink/80">
                点击提交后会直接创建真实评审任务，并跳转到运行状态页。
              </p>
            </div>
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

          {submitError ? (
            <div className="mt-5 rounded-3xl border border-wine/20 bg-wine/10 px-4 py-4 text-sm leading-6 text-wine">
              {submitError}
            </div>
          ) : null}
        </SectionCard>
      </section>

      <SectionCard
        title="方案录入"
        eyebrow="2 到 4 个方案最合适"
        description="每个方案都应该真的能比较。为了让团队易用，渠道可直接写成逗号分隔的一行文本。"
        action={
          <button className="secondary-button" type="button" onClick={addCampaign}>
            新增方案
          </button>
        }
      >
        <div className="space-y-5">
          {campaigns.map((campaign, index) => (
            <article key={campaign.id} className="rounded-panel border border-line/80 bg-cream px-4 py-4 transition-colors focus-within:border-mist/50 sm:px-5">
              <div className="mb-4 flex flex-col gap-3 border-b border-line/50 pb-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3">
                  <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line/70 bg-paper text-xs font-semibold text-coffee">
                    {index + 1}
                  </span>
                  <div>
                    <p className="section-label">方案 {index + 1}</p>
                    <input
                      className="mt-1.5 w-full border-none bg-transparent p-0 font-serif text-2xl font-semibold text-coffee placeholder:text-ink/35 focus:outline-none"
                      value={campaign.name}
                      onChange={(event) => updateCampaign(index, 'name', event.target.value)}
                      placeholder="请输入方案名"
                    />
                  </div>
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
                    placeholder="例如：小红书, 抖音, 天猫"
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
          eyebrow="真实提交"
          description="这里会直接调用后端创建任务。提交后页面自动跳到运行状态，并开始轮询进度。"
        >
          <div className="space-y-4">
            <div className="rounded-3xl border border-line/70 bg-cream px-4 py-4">
              <p className="font-semibold text-coffee">{reviewName || '未命名评审'}</p>
              <p className="mt-2 text-sm leading-6 text-ink/80">
                当前共录入 {campaigns.length} 个方案。请确认每个方案都真的有可比较差异。
              </p>
            </div>

            <div className="rounded-3xl border border-mist/25 bg-mist-soft/40 px-4 py-4">
              <p className="font-semibold text-coffee">提交前提醒</p>
              <p className="mt-2 text-sm leading-6 text-ink/80">
                如果只有写法不同、但受众和场景没有区别，建议继续补信息，不要急着进入比较。
              </p>
            </div>

            <button
              className="primary-button w-full justify-center"
              type="button"
              disabled={!canSubmit || isSubmitting}
              onClick={submitReview}
            >
              {isSubmitting ? '正在创建评审任务...' : '提交并进入运行状态'}
            </button>
          </div>
        </SectionCard>
      </section>
    </div>
  )
}
