import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, Zap, Search, Layers, AlertCircle, ImagePlus, X, Loader2, RefreshCcw } from 'lucide-react'
import { type RacePayload, type EvaluatePayload, type CampaignPlan, saveRaceState, saveEvaluateState, evaluateCampaigns, saveBothModeState, uploadCampaignImage, getIterateState, clearIterateState } from '../lib/api'
import { saveHomeForm, loadHomeForm, clearHomeForm } from '../lib/homeFormStorage'
import { uuid } from '../utils'

type SimulationMode = 'race' | 'evaluate' | 'both'

const PERSONA_PREVIEW: Record<string, string[]> = {
  moodyplus: [
    '日抛隐形眼镜老用户',
    'Acuvue Define 现有用户',
    '眼健康关注者',
    '办公室长时间佩戴用户',
    '运动爱好者',
    '敏感眼用户',
    '科技感知者',
    '医疗合规顾问',
    '日常佩戴体验者',
  ],
  colored_lenses: [
    '美瞳新用户（颜值驱动）',
    '价格敏感用户',
    '美妆博主',
    'Coser/特殊场合用户',
    '自然放大需求用户',
    '彩妆博主',
    '摄影师/视觉创作者',
    '亚文化爱好者',
  ],
}

const MODE_OPTIONS: Array<{ value: SimulationMode; label: string; desc: string; time: string; icon: typeof Zap }> = [
  { value: 'race', label: '快速推演', desc: '基于历史基线数据快速排序', time: '~15 秒', icon: Zap },
  { value: 'evaluate', label: '深度评审', desc: '多人格评审团 + 两两对比', time: '~3 分钟', icon: Search },
  { value: 'both', label: '联合推演', desc: '同时运行快速推演和深度评审', time: '~3 分钟', icon: Layers },
]

type UploadedPlanImage = {
  id: string
  name: string
  previewUrl: string
  uploadedUrl?: string
  status: 'uploading' | 'ready' | 'error'
  error?: string
}

const DEFAULT_PLAN: Omit<CampaignPlan, 'id'> = {
  name: '',
  theme: 'science_credibility',
  platform: 'facebook',
  channel_family: 'social_seed',
  budget: 50000,
  image_paths: [],
}

function makePlan(overrides: Partial<CampaignPlan> = {}): CampaignPlan {
  return {
    id: uuid(),
    ...DEFAULT_PLAN,
    ...overrides,
  }
}

function makeImageDraft(file: File): UploadedPlanImage {
  return {
    id: uuid(),
    name: file.name,
    previewUrl: URL.createObjectURL(file),
    status: 'uploading',
  }
}

export function HomePage() {
  const navigate = useNavigate()

  const savedForm = loadHomeForm()

  const [mode, setMode] = useState<SimulationMode>(savedForm?.mode ?? 'race')

  const [market, setMarket] = useState(savedForm?.market ?? 'cn')
  const [productLine, setProductLine] = useState(savedForm?.productLine ?? 'moodyplus')
  const [audience] = useState('general')
  const [sortBy, setSortBy] = useState<RacePayload['sort_by']>(savedForm?.sortBy ?? 'roas_mean')
  const [seasonTag, setSeasonTag] = useState(savedForm?.seasonTag ?? '')
  const [briefType, setBriefType] = useState<'brand' | 'seeding' | 'conversion' | ''>(
    savedForm?.briefType ?? ''
  )
  const [draftSetId] = useState(() => `race_${uuid()}`)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [iterateState] = useState(() => getIterateState())

  const [plans, setPlans] = useState<CampaignPlan[]>(() => {
    if (savedForm?.plans && savedForm.plans.length > 0) return savedForm.plans
    return [
      makePlan({ name: 'Plan A', theme: 'science_credibility' }),
      makePlan({ name: 'Plan B', theme: 'comfort_beauty', platform: 'instagram' }),
    ]
  })
  const [planImages, setPlanImages] = useState<Record<string, UploadedPlanImage[]>>(() =>
    Object.fromEntries(
      plans.map((plan) => [plan.id ?? uuid(), []]),
    ),
  )

  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({})
  const imageMapRef = useRef(planImages)

  useEffect(() => {
    imageMapRef.current = planImages
  }, [planImages])

  useEffect(() => {
    return () => {
      Object.values(imageMapRef.current)
        .flat()
        .forEach((image) => URL.revokeObjectURL(image.previewUrl))
    }
  }, [])

  const addPlan = () => {
    if (plans.length >= 5) return
    const nextPlan = makePlan({ name: `Plan ${String.fromCharCode(65 + plans.length)}` })
    setPlans((current) => [...current, nextPlan])
    setPlanImages((current) => ({
      ...current,
      [nextPlan.id as string]: [],
    }))
  }

  const removePlan = (index: number) => {
    if (plans.length <= 1) return
    const removedPlan = plans[index]
    const removedPlanId = removedPlan.id
    if (!removedPlanId) return

    imageMapRef.current[removedPlanId]?.forEach((image) => URL.revokeObjectURL(image.previewUrl))

    setPlans((current) => current.filter((_, currentIndex) => currentIndex !== index))
    setPlanImages((current) => {
      const next = { ...current }
      delete next[removedPlanId]
      delete fileInputRefs.current[removedPlanId]
      return next
    })
  }

  const updatePlan = (index: number, updates: Partial<CampaignPlan>) => {
    const nextPlans = plans.map((plan, currentIndex) =>
      currentIndex === index ? { ...plan, ...updates } : plan,
    )
    setPlans(nextPlans)
    persistForm({ plans: nextPlans })
  }

  const handleAddImages = async (plan: CampaignPlan, newFiles: FileList | null) => {
    const planId = plan.id
    if (!planId || !newFiles) return

    const existingImages = imageMapRef.current[planId] ?? []
    const allowedFiles = Array.from(newFiles).slice(0, Math.max(0, 5 - existingImages.length))
    if (allowedFiles.length === 0) return

    setUploadError(null)

    const drafts = allowedFiles.map((file) => ({
      file,
      image: makeImageDraft(file),
    }))

    setPlanImages((current) => ({
      ...current,
      [planId]: [...(current[planId] ?? []), ...drafts.map((draft) => draft.image)],
    }))

    for (const draft of drafts) {
      try {
        const uploaded = await uploadCampaignImage(draft.file, draftSetId, planId)
        const imageStillTracked = (imageMapRef.current[planId] ?? []).some(
          (image) => image.id === draft.image.id,
        )
        if (!imageStillTracked) continue

        setPlanImages((current) => ({
          ...current,
          [planId]: (current[planId] ?? []).map((image) =>
            image.id === draft.image.id
              ? {
                  ...image,
                  status: 'ready',
                  uploadedUrl: uploaded.url,
                }
              : image,
          ),
        }))

        setPlans((current) =>
          current.map((currentPlan) =>
            currentPlan.id === planId
              ? {
                  ...currentPlan,
                  image_paths: [...(currentPlan.image_paths ?? []), uploaded.url],
                }
              : currentPlan,
          ),
        )
      } catch (error) {
        const message = error instanceof Error ? error.message : '图片上传失败'
        const imageStillTracked = (imageMapRef.current[planId] ?? []).some(
          (image) => image.id === draft.image.id,
        )
        if (!imageStillTracked) continue
        setUploadError(message)
        setPlanImages((current) => ({
          ...current,
          [planId]: (current[planId] ?? []).map((image) =>
            image.id === draft.image.id
              ? {
                  ...image,
                  status: 'error',
                  error: message,
                }
              : image,
          ),
        }))
      }
    }
  }

  const handleRemoveImage = (plan: CampaignPlan, imageId: string) => {
    const planId = plan.id
    if (!planId) return

    const imageToRemove = (imageMapRef.current[planId] ?? []).find((image) => image.id === imageId)
    if (!imageToRemove) return

    URL.revokeObjectURL(imageToRemove.previewUrl)

    setPlanImages((current) => ({
      ...current,
      [planId]: (current[planId] ?? []).filter((image) => image.id !== imageId),
    }))

    if (imageToRemove.uploadedUrl) {
      setPlans((current) =>
        current.map((currentPlan) =>
          currentPlan.id === planId
            ? {
                ...currentPlan,
                image_paths: (currentPlan.image_paths ?? []).filter(
                  (imagePath) => imagePath !== imageToRemove.uploadedUrl,
                ),
              }
            : currentPlan,
        ),
      )
    }
  }

  const hasPendingUploads = Object.values(planImages).some((images) =>
    images.some((image) => image.status === 'uploading'),
  )
  const uploadedAssetCount = Object.values(planImages).reduce(
    (count, images) => count + images.filter((image) => image.status === 'ready').length,
    0,
  )

  const persistForm = (overrides: Partial<Parameters<typeof saveHomeForm>[0]> = {}) => {
    saveHomeForm({
      mode,
      market,
      productLine,
      sortBy,
      seasonTag,
      briefType,
      plans,
      ...overrides,
    })
  }

  const buildRacePayload = (): RacePayload => ({
    market,
    product_line: productLine,
    audience_segment: audience,
    sort_by: sortBy,
    include_hypothesis: true,
    plans: plans
      .filter((plan) => plan.name.trim() && plan.theme)
      .map((plan) => ({
        ...plan,
        image_paths: plan.image_paths ?? [],
      })),
    ...(seasonTag ? { season_tag: seasonTag } : {}),
  })

  const buildEvaluatePayload = (): { payload: EvaluatePayload; setId: string } => {
    const setId = `eval_${uuid()}`
    const payload: EvaluatePayload = {
      set_id: setId,
      campaigns: plans
        .filter((p) => p.name.trim() && p.theme)
        .map((p) => ({
          campaign_id: p.id ?? uuid(),
          name: p.name,
          description: `${p.theme} / ${p.platform}`,
          image_paths: p.image_paths ?? [],
        })),
      category: productLine,
      ...(iterateState?.parentSetId ? { parent_set_id: iterateState.parentSetId } : {}),
      ...(briefType ? { brief_type: briefType as 'brand' | 'seeding' | 'conversion' } : {}),
    }
    return { payload, setId }
  }

  const handleSubmit = async () => {
    // Clear iterate state on any submission
    clearIterateState()

    if (mode === 'race') {
      const payload = buildRacePayload()
      saveRaceState({ payload })
      clearHomeForm()
      navigate('/running')
      return
    }

    if (mode === 'evaluate') {
      if (!briefType) {
        setUploadError('请选择 Brief 类型（品牌传播 / 达人种草 / 转化拉新）')
        return
      }
      setSubmitting(true)
      try {
        const { payload, setId } = buildEvaluatePayload()
        const res = await evaluateCampaigns(payload)
        saveEvaluateState({ taskId: res.task_id, setId, payload })
        clearHomeForm()
        navigate('/evaluate')
      } catch {
        setSubmitting(false)
      }
      return
    }

    // Both mode: await evaluate before navigate so evaluateTaskId is in localStorage
    if (!briefType) {
      setUploadError('请选择 Brief 类型（品牌传播 / 达人种草 / 转化拉新）')
      return
    }
    const racePayload = buildRacePayload()
    saveRaceState({ payload: racePayload })

    const { payload: evalPayload, setId: evalSetId } = buildEvaluatePayload()
    setSubmitting(true)

    try {
      const res = await evaluateCampaigns(evalPayload)
      saveEvaluateState({ taskId: res.task_id, setId: evalSetId, payload: evalPayload })
      saveBothModeState({ evaluateTaskId: res.task_id, evaluateSetId: evalSetId })
    } catch {
      // Evaluate POST failed silently — Race path still available
    } finally {
      setSubmitting(false)
      clearHomeForm()
      navigate('/running')
    }
    return
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-10 items-start">
      <div className="space-y-10">
        {iterateState && (
          <section className="lab-card p-4 flex items-center gap-3 bg-violet-50 border-violet-200">
            <RefreshCcw className="h-5 w-5 text-violet-600 shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-violet-700">基于上一版本迭代</h3>
              <p className="text-xs text-violet-600/70">请修改方案后重新提交，系统将自动关联为同一 campaign 的新版本</p>
            </div>
            <button
              onClick={() => { clearIterateState(); window.location.reload() }}
              className="ml-auto text-xs text-violet-600 hover:text-violet-800 underline shrink-0"
            >
              取消迭代
            </button>
          </section>
        )}

        <section className="space-y-4">
          <h1 className="font-display text-4xl text-primary font-semibold">营销实验室</h1>
          <p className="text-muted-foreground text-lg leading-relaxed max-w-2xl text-balance">
            最多评估 5 个策略方向。引擎优先基于
            <strong className="text-primary font-medium mx-1">历史基线数据</strong>（经验漏斗数据）进行排序，
            辅以<span className="italic">模型假设</span>提供认知偏移与风险预警。
          </p>
        </section>

        <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {MODE_OPTIONS.map((opt) => {
            const Icon = opt.icon
            const selected = mode === opt.value
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => { setMode(opt.value); persistForm({ mode: opt.value }) }}
                className={`lab-card p-4 cursor-pointer border-2 transition-all text-left ${
                  selected
                    ? 'border-primary bg-primary/5'
                    : 'border-transparent hover:border-border'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Icon className="h-4 w-4 text-primary" />
                  <span className="text-base font-semibold">{opt.label}</span>
                </div>
                <p className="text-sm text-muted-foreground">{opt.desc}</p>
                <span className="inline-block mt-2 text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">{opt.time}</span>
              </button>
            )
          })}
        </section>

        <section className="lab-card p-6 flex flex-wrap gap-8 items-end">
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">市场</label>
            <select
              value={market}
              onChange={(event) => { setMarket(event.target.value); persistForm({ market: event.target.value }) }}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="cn">中国大陆</option>
              <option value="us">美国</option>
              <option value="sea">东南亚</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">品类</label>
            <select
              value={productLine}
              onChange={(event) => { setProductLine(event.target.value); persistForm({ productLine: event.target.value }) }}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="moodyplus">透明片（moodyPlus）</option>
              <option value="colored_lenses">彩片</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">优化目标</label>
            <select
              value={sortBy}
              onChange={(event) => {
                const v = event.target.value as 'roas_mean' | 'purchase_rate' | 'revenue_mean' | 'cvr_mean'
                setSortBy(v)
                persistForm({ sortBy: v })
              }}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="roas_mean">ROAS（均值）</option>
              <option value="revenue_mean">收入潜力</option>
              <option value="purchase_rate">转化率</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">季节场景</label>
            <select
              value={seasonTag}
              onChange={(event) => { setSeasonTag(event.target.value); persistForm({ seasonTag: event.target.value }) }}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="">常规（无季节）</option>
              <option value="618">618 大促</option>
              <option value="double11">双十一</option>
              <option value="38">38 女王节</option>
              <option value="99">99 划算节</option>
              <option value="cny">春节 / CNY</option>
            </select>
          </div>
        </section>

        {(mode === 'evaluate' || mode === 'both') && (
          <section className="lab-card p-6 space-y-3">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Brief 类型 <span className="text-red-500">*</span>
              </label>
              <div className="flex gap-3 flex-wrap">
                {[
                  { value: 'brand', label: '品牌传播' },
                  { value: 'seeding', label: '达人种草' },
                  { value: 'conversion', label: '转化拉新' },
                ].map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => {
                      setBriefType(value as 'brand' | 'seeding' | 'conversion')
                      persistForm({ briefType: value as 'brand' | 'seeding' | 'conversion' })
                      setUploadError(null)
                    }}
                    className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                      briefType === value
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {!briefType && uploadError?.includes('Brief') && (
                <p className="text-sm text-red-500">请选择 Brief 类型</p>
              )}
            </div>
          </section>
        )}

        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-2xl text-primary">策略方向</h2>
            <span className="text-sm text-muted-foreground">{plans.length} / 5</span>
          </div>

          <div className="space-y-4">
            {plans.map((plan, index) => {
              const planId = plan.id as string
              const images = planImages[planId] ?? []

              return (
                <div
                  key={planId}
                  className="lab-card p-6 relative group border-l-4 border-l-border focus-within:border-l-primary transition-all"
                >
                  <button
                    onClick={() => removePlan(index)}
                    disabled={plans.length <= 1}
                    className="absolute right-4 top-4 text-muted-foreground hover:text-accent opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
                    <div className="space-y-1.5 col-span-1 md:col-span-2">
                      <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">方案名称</label>
                      <input
                        type="text"
                        value={plan.name}
                        onChange={(event) => updatePlan(index, { name: event.target.value })}
                        placeholder="例：春季科学种草"
                        className="lab-input text-lg font-display"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">认知主题</label>
                      <select
                        value={plan.theme}
                        onChange={(event) => updatePlan(index, { theme: event.target.value })}
                        className="lab-input text-sm"
                      >
                        <option value="science_credibility">科学与可信度</option>
                        <option value="comfort_beauty">舒适与美感</option>
                        <option value="aesthetic">审美与视觉</option>
                        <option value="price">价格与性价比</option>
                        <option value="social">社交背书 / KOL</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">主要平台</label>
                      <select
                        value={plan.platform}
                        onChange={(event) => updatePlan(index, { platform: event.target.value })}
                        className="lab-input text-sm"
                      >
                        <option value="facebook">Facebook</option>
                        <option value="instagram">Instagram</option>
                        <option value="google">Google</option>
                        <option value="youtube">YouTube</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">预算分配（CNY）</label>
                      <input
                        type="number"
                        value={plan.budget}
                        onChange={(event) => updatePlan(index, { budget: Number(event.target.value) })}
                        className="lab-input text-sm font-mono"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">渠道类型</label>
                      <select
                        value={plan.channel_family}
                        onChange={(event) => updatePlan(index, { channel_family: event.target.value })}
                        className="lab-input text-sm"
                      >
                        <option value="social_seed">社交种草 / KOC</option>
                        <option value="short_video">短视频</option>
                        <option value="longform_content">长内容</option>
                        <option value="marketplace">电商平台</option>
                        <option value="influencer">达人 / KOL</option>
                        <option value="search">搜索广告</option>
                      </select>
                    </div>
                  </div>

                  <div className="mt-6 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
                          视觉参考素材（最多 5 张）
                        </label>
                        <p className="text-xs text-muted-foreground">
                          上传后会用多模态模型分析视觉内容。当基线分数接近时，图片内容可差异化影响排序。
                        </p>
                      </div>
                      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        {images.filter((image) => image.status === 'ready').length} / 5 Ready
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-3">
                      {images.map((image) => (
                        <div
                          key={image.id}
                          className={`relative w-24 h-24 rounded-sm overflow-hidden border transition-colors group/img ${
                            image.status === 'error'
                              ? 'border-red-300 bg-red-50'
                              : image.status === 'uploading'
                                ? 'border-primary/40 bg-primary/5'
                                : 'border-border'
                          }`}
                        >
                          <img
                            src={image.previewUrl}
                            alt={image.name}
                            className={`w-full h-full object-cover ${image.status === 'uploading' ? 'opacity-80' : ''}`}
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveImage(plan, image.id)}
                            className="absolute top-1 right-1 bg-black/60 text-white rounded-full p-1 opacity-0 group-hover/img:opacity-100 transition-opacity"
                          >
                            <X className="h-3 w-3" />
                          </button>
                          <div className="absolute inset-x-0 bottom-0 bg-black/60 text-white px-2 py-1 text-[10px] leading-tight">
                            {image.status === 'uploading' && (
                              <span className="inline-flex items-center gap-1">
                                <Loader2 className="h-3 w-3 animate-spin" />
                                上传中
                              </span>
                            )}
                            {image.status === 'ready' && <span>已接入方案</span>}
                            {image.status === 'error' && <span>{image.error ?? '上传失败'}</span>}
                          </div>
                        </div>
                      ))}

                      {images.length < 5 && (
                        <button
                          type="button"
                          onClick={() => fileInputRefs.current[planId]?.click()}
                          className="w-24 h-24 rounded-sm border border-dashed border-border flex flex-col items-center justify-center gap-2 text-muted-foreground hover:text-primary hover:border-primary hover:bg-primary/5 transition-colors"
                        >
                          <ImagePlus className="h-5 w-5" />
                          <span className="text-[11px] font-medium">添加素材</span>
                        </button>
                      )}
                    </div>

                    <input
                      ref={(element) => {
                        fileInputRefs.current[planId] = element
                      }}
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={(event) => {
                        void handleAddImages(plan, event.target.files)
                        event.target.value = ''
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          {plans.length < 5 && (
            <button
              onClick={addPlan}
              className="w-full py-4 border border-dashed border-border rounded-sm text-muted-foreground hover:text-primary hover:border-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
            >
              <Plus className="h-4 w-4" /> 添加策略方向
            </button>
          )}
        </section>
      </div>

      <div className="sticky top-24 space-y-6">
        {/* 品类人格预览 */}
        <div className="lab-card p-5 space-y-3">
          <h3 className="text-xs uppercase tracking-wider font-bold text-primary">
            评审团
            <span className="ml-2 text-muted-foreground font-normal normal-case">
              {productLine === 'moodyplus' ? '透明片' : '彩片'} · {PERSONA_PREVIEW[productLine].length} 位
            </span>
          </h3>
          <ul className="space-y-1.5">
            {PERSONA_PREVIEW[productLine].map((name, i) => (
              <li key={i} className="text-sm text-muted-foreground flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] flex items-center justify-center shrink-0 font-mono">
                  {i + 1}
                </span>
                {name}
              </li>
            ))}
          </ul>
        </div>

        <div className="lab-card p-5 space-y-5 bg-card/50">
          <div>
            <h3 className="text-xs uppercase tracking-wider font-bold text-primary mb-3">评估矩阵</h3>
            <ul className="space-y-3 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <span className="baseline-tag shrink-0 mt-0.5">第一层</span>
                <span>历史漏斗基线 & 经验对照</span>
              </li>
              <li className="flex gap-2">
                <span className="hypothesis-tag shrink-0 mt-0.5">第二层</span>
                <span>认知模型假设（实验性）</span>
              </li>
              <li className="flex gap-2 text-xs">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-accent" />
                <span>图片素材会参与视觉分析。当多方案基线分数接近时，素材内容可透明地影响排序差异。</span>
              </li>
            </ul>
          </div>

          <div className="rounded-sm border border-border/60 bg-background/70 px-4 py-3 space-y-2">
            <div className="flex items-center justify-between text-xs uppercase tracking-wider text-muted-foreground">
              <span>Reference Assets</span>
              <span>{uploadedAssetCount}</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {hasPendingUploads
                ? '有素材正在上传，建议等待上传完成后再开始评估。'
                : uploadedAssetCount > 0
                  ? '素材已接入到方案，评估时会分析视觉内容并参与判别。'
                  : '你可以为每个方案附加素材图，图片内容会参与评估判别。'}
            </p>
            {uploadError && <p className="text-xs text-red-600">{uploadError}</p>}
          </div>

          <div className="pt-4 border-t border-border">
            <button
              onClick={() => void handleSubmit()}
              disabled={plans.length === 0 || hasPendingUploads || submitting}
              className="lab-button lab-button-primary w-full h-12 text-base gap-2 group disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {hasPendingUploads || submitting ? (
                <Loader2 className="h-4 w-4 text-accent-foreground animate-spin" />
              ) : (
                <Zap className="h-4 w-4 text-accent-foreground group-hover:animate-pulse" />
              )}
              {hasPendingUploads
                ? '等待素材上传完成'
                : mode === 'evaluate'
                  ? '开始深度评审'
                  : mode === 'both'
                    ? '开始联合推演'
                    : '开始评估'}
            </button>
            <p className="text-[10px] text-center text-muted-foreground mt-3 uppercase tracking-wider">
              预计需要约 {mode === 'race' ? '15 秒' : '3 分钟'}计算时间
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
