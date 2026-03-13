import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { SectionCard } from '../components/ui/SectionCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import {
  evaluateCampaigns,
  parseBrief,
  saveLatestReviewSession,
  uploadImage,
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
  const [draftSetId, setDraftSetId] = useState(() => crypto.randomUUID())
  const [reviewName, setReviewName] = useState(reviewPreset.reviewName)
  const [context, setContext] = useState(reviewPreset.context)
  const [campaigns, setCampaigns] = useState(initialCampaignDrafts)
  const [submitError, setSubmitError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [touched, setTouched] = useState<Record<string, boolean>>({})
  const [showErrors, setShowErrors] = useState(false)
  const [briefMode, setBriefMode] = useState<Record<string, boolean>>({})
  const [briefTexts, setBriefTexts] = useState<Record<string, string>>({})
  const [parsingIndex, setParsingIndex] = useState<number | null>(null)
  const [parseError, setParseError] = useState<Record<string, string>>({})
  const [campaignImages, setCampaignImages] = useState<Record<string, File[]>>({})
  const [briefNeedsConfirmation, setBriefNeedsConfirmation] = useState<Record<string, boolean>>({})

  const handleImageUpload = (campaignId: string, files: FileList | null) => {
    if (!files) return
    const validFiles = Array.from(files).filter(f =>
      ['image/jpeg', 'image/png', 'image/webp'].includes(f.type)
    ).slice(0, 5)
    setCampaignImages(prev => ({
      ...prev,
      [campaignId]: [...(prev[campaignId] || []), ...validFiles].slice(0, 5)
    }))
  }

  const removeImage = (campaignId: string, imageIndex: number) => {
    setCampaignImages(prev => ({
      ...prev,
      [campaignId]: (prev[campaignId] || []).filter((_, i) => i !== imageIndex)
    }))
  }

  const isBriefMode = (cid: string) => briefMode[cid] !== false // default true
  const toggleMode = (cid: string) =>
    setBriefMode((prev) => ({ ...prev, [cid]: !isBriefMode(cid) }))

  const handleParseBrief = async (index: number, campaignId: string) => {
    const text = briefTexts[campaignId]?.trim()
    if (!text) return
    setParsingIndex(index)
    setParseError((prev) => ({ ...prev, [campaignId]: '' }))
    try {
      const result = await parseBrief({
        brief_text: text,
        product_line: campaigns[index].productLine,
      })
      const p = result.parsed
      setCampaigns((current) =>
        current.map((c) =>
          c.id === campaignId
            ? {
                ...c,
                name: p.name || c.name,
                targetAudience: p.target_audience || c.targetAudience,
                coreMessage: p.core_message || c.coreMessage,
                channels: Array.isArray(p.channels) ? p.channels.join(', ') : (p.channels || c.channels),
                creativeDirection: p.creative_direction || c.creativeDirection,
                budgetRange: p.budget_range || c.budgetRange,
                promoMechanic: p.promo_mechanic || c.promoMechanic,
                kvDescription: p.kv_description || c.kvDescription,
              }
            : c,
        ),
      )
      setBriefMode((prev) => ({ ...prev, [campaignId]: false }))
      setBriefNeedsConfirmation((prev) => ({ ...prev, [campaignId]: true }))
    } catch (err) {
      const msg = err instanceof Error ? err.message : '解析失败，请切换到高级模式手动填写'
      setParseError((prev) => ({ ...prev, [campaignId]: msg }))
    } finally {
      setParsingIndex(null)
    }
  }

  const confirmBrief = (campaignId: string) => {
    setBriefNeedsConfirmation((prev) => ({ ...prev, [campaignId]: false }))
  }

  const fieldKey = (index: number, field: string) => `${index}-${field}`
  const markTouched = (index: number, field: string) =>
    setTouched((prev) => ({ ...prev, [fieldKey(index, field)]: true }))
  const isFieldError = (index: number, field: string, value: string) =>
    (touched[fieldKey(index, field)] || showErrors) && !value.trim()

  // P0 fix: only name + coreMessage required
  const campaignsWithEnoughInput = campaigns.filter(
    (campaign) =>
      campaign.name.trim() &&
      campaign.coreMessage.trim(),
  ).length

  const hasUnconfirmedBrief = useMemo(
    () => Object.values(briefNeedsConfirmation).some(Boolean),
    [briefNeedsConfirmation],
  )

  const canSubmit = campaigns.length >= 2 && campaignsWithEnoughInput === campaigns.length && !hasUnconfirmedBrief

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
    const cid = campaigns[index].id
    setCampaigns((current) => current.filter((_, currentIndex) => currentIndex !== index))
    setBriefNeedsConfirmation((prev) => { const next = { ...prev }; delete next[cid]; return next })
    setCampaignImages((prev) => { const next = { ...prev }; delete next[cid]; return next })
    setBriefMode((prev) => { const next = { ...prev }; delete next[cid]; return next })
    setBriefTexts((prev) => { const next = { ...prev }; delete next[cid]; return next })
    setParseError((prev) => { const next = { ...prev }; delete next[cid]; return next })
  }

  const submitReview = async () => {
    setShowErrors(true)
    if (!canSubmit) return
    if (isSubmitting) return

    setIsSubmitting(true)
    setSubmitError('')

    try {
      const payloadCampaigns = campaigns.map(toPayloadCampaign)

      // Upload images with set_id and campaign_id binding
      for (let i = 0; i < campaigns.length; i++) {
        const cid = campaigns[i].id
        const images = campaignImages[cid]
        if (images?.length) {
          const paths: string[] = []
          for (const file of images) {
            try {
              const result = await uploadImage(file, draftSetId, cid.trim())
              paths.push(result.path)
            } catch {
              // Image upload failure is non-fatal
            }
          }
          if (paths.length) {
            payloadCampaigns[i] = { ...payloadCampaigns[i], image_paths: paths } as CampaignInput & { image_paths: string[] }
          }
        }
      }

      const payload = {
        set_id: draftSetId,
        context: [reviewName.trim(), context.trim()].filter(Boolean).join('\n\n'),
        campaigns: payloadCampaigns,
      }
      const response = await evaluateCampaigns(payload)

      saveLatestReviewSession({
        taskId: response.task_id,
        setId: response.set_id,
        reviewName: reviewName.trim(),
      })

      setDraftSetId(crypto.randomUUID())
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
              <p className="field-label">必填完成</p>
              <p className="mt-3 font-serif text-2xl font-semibold text-coffee">
                {campaignsWithEnoughInput} / {campaigns.length}
              </p>
              <p className="mt-2 text-sm leading-6 text-ink/80">每个方案需填写名称和核心信息。</p>
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
              把方案写成"可以比较"的输入，而不是只写一堆看起来高级但没法评的抽象词。
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
                    <div>
                      <input
                        className={`mt-1.5 w-full border-none bg-transparent p-0 font-serif text-2xl font-semibold text-coffee placeholder:text-ink/35 focus:outline-none ${isFieldError(index, 'name', campaign.name) ? 'border-b-2 !border-red-400' : ''}`}
                        style={isFieldError(index, 'name', campaign.name) ? { borderBottom: '2px solid #f87171' } : undefined}
                        value={campaign.name}
                        onChange={(event) => updateCampaign(index, 'name', event.target.value)}
                        onBlur={() => markTouched(index, 'name')}
                        placeholder="请输入方案名"
                      />
                      {isFieldError(index, 'name', campaign.name) && <p className="text-xs text-red-500 mt-1">此项必填</p>}
                    </div>
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
                  <button
                    className="secondary-button text-xs"
                    type="button"
                    onClick={() => toggleMode(campaign.id)}
                  >
                    {isBriefMode(campaign.id) ? '高级模式' : '简述模式'}
                  </button>
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

              {briefNeedsConfirmation[campaign.id] && (
                <div className="mb-4 flex items-center gap-3 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3">
                  <span className="text-sm text-amber-800">Brief 已解析为结构化字段，请检查后确认</span>
                  <button
                    type="button"
                    className="ml-auto rounded-xl bg-amber-600 px-3 py-1 text-xs font-semibold text-white hover:bg-amber-700"
                    onClick={() => confirmBrief(campaign.id)}
                  >
                    确认解析结果
                  </button>
                </div>
              )}

              {isBriefMode(campaign.id) ? (
                <div className="space-y-3">
                  <label className="space-y-2">
                    <span className="field-label">方案简述</span>
                    <textarea
                      className="field-textarea"
                      rows={5}
                      value={briefTexts[campaign.id] ?? ''}
                      onChange={(e) => setBriefTexts((prev) => ({ ...prev, [campaign.id]: e.target.value }))}
                      placeholder={'用自然语言描述你的方案，例如：\n"针对大学生群体推一波椰糖棕色的日抛，主打自然素颜感，在小红书上做种草，预算不高，想用学生价的促销来拉新客"'}
                    />
                  </label>
                  <div className="flex items-center gap-3">
                    <button
                      className="primary-button"
                      type="button"
                      disabled={!briefTexts[campaign.id]?.trim() || parsingIndex === index}
                      onClick={() => handleParseBrief(index, campaign.id)}
                    >
                      {parsingIndex === index ? '解析中...' : '解析为结构化字段'}
                    </button>
                    <span className="text-xs text-ink/50">解析后会自动切换到高级模式供你确认和编辑</span>
                  </div>
                  {parseError[campaign.id] ? (
                    <p className="text-sm text-wine">{parseError[campaign.id]}</p>
                  ) : null}
                </div>
              ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                  <label className="space-y-2 lg:col-span-2">
                    <span className="field-label">核心信息 *</span>
                    <textarea
                      className={`field-textarea ${isFieldError(index, 'coreMessage', campaign.coreMessage) ? 'border-red-400 ring-1 ring-red-300' : ''}`}
                      rows={3}
                      value={campaign.coreMessage}
                      onChange={(event) => updateCampaign(index, 'coreMessage', event.target.value)}
                      onBlur={() => markTouched(index, 'coreMessage')}
                    />
                    {isFieldError(index, 'coreMessage', campaign.coreMessage) && <p className="text-xs text-red-500 mt-1">此项必填</p>}
                  </label>

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
                    <span className="field-label">创意方向</span>
                    <input
                      className="field-input"
                      value={campaign.creativeDirection}
                      onChange={(event) => updateCampaign(index, 'creativeDirection', event.target.value)}
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

                  <label className="space-y-2">
                    <span className="field-label">KV 描述</span>
                    <textarea
                      className="field-textarea"
                      rows={3}
                      value={campaign.kvDescription}
                      onChange={(event) => updateCampaign(index, 'kvDescription', event.target.value)}
                    />
                  </label>

                  <div className="lg:col-span-2 space-y-2">
                    <span className="field-label">素材图片（可选，最多 5 张）</span>
                    <div className="flex flex-wrap gap-3">
                      {(campaignImages[campaign.id] || []).map((file, imgIdx) => (
                        <div key={imgIdx} className="relative group">
                          <img
                            src={URL.createObjectURL(file)}
                            alt={file.name}
                            className="h-20 w-20 rounded-xl object-cover border border-line/50"
                          />
                          <button
                            type="button"
                            onClick={() => removeImage(campaign.id, imgIdx)}
                            className="absolute -top-1.5 -right-1.5 hidden group-hover:flex h-5 w-5 items-center justify-center rounded-full bg-wine text-white text-xs"
                          >
                            x
                          </button>
                        </div>
                      ))}
                      {(campaignImages[campaign.id] || []).length < 5 && (
                        <label className="flex h-20 w-20 cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-line/50 text-ink/30 hover:border-mist/50 hover:text-ink/50 transition-colors">
                          <span className="text-2xl">+</span>
                          <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            multiple
                            className="hidden"
                            onChange={(e) => handleImageUpload(campaign.id, e.target.files)}
                          />
                        </label>
                      )}
                    </div>
                  </div>
                </div>
              )}
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
              {isSubmitting
                ? '正在创建评审任务...'
                : hasUnconfirmedBrief
                  ? '请先确认所有 Brief 解析结果'
                  : showErrors && !canSubmit
                    ? '请先完成必填项（名称 + 核心信息）'
                    : '提交并进入运行状态'}
            </button>
          </div>
        </SectionCard>
      </section>
    </div>
  )
}
