import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, Zap, AlertCircle, ImagePlus, X } from 'lucide-react'
import { type RacePayload, type CampaignPlan, saveRaceState } from '../lib/api'

type PlanImages = { files: File[]; previews: string[] }

const DEFAULT_PLAN: CampaignPlan = {
  name: '',
  theme: 'science_credibility',
  platform: 'facebook',
  channel_family: 'social_seed',
  budget: 50000,
}

export function HomePage() {
  const navigate = useNavigate()
  
  const [market, setMarket] = useState('cn')
  const [productLine, setProductLine] = useState('moodyplus')
  const [audience] = useState('general')
  const [sortBy, setSortBy] = useState<RacePayload['sort_by']>('roas_mean')
  const [seasonTag, setSeasonTag] = useState('')
  
  const [plans, setPlans] = useState<CampaignPlan[]>([
    { ...DEFAULT_PLAN, name: 'Plan A', theme: 'science_credibility' },
    { ...DEFAULT_PLAN, name: 'Plan B', theme: 'comfort_beauty', platform: 'instagram' },
  ])
  const [planImages, setPlanImages] = useState<PlanImages[]>([
    { files: [], previews: [] },
    { files: [], previews: [] },
  ])
  const fileInputRefs = useRef<(HTMLInputElement | null)[]>([])

  const addPlan = () => {
    if (plans.length >= 5) return
    setPlans([...plans, { ...DEFAULT_PLAN, name: `Plan ${String.fromCharCode(65 + plans.length)}` }])
    setPlanImages([...planImages, { files: [], previews: [] }])
  }

  const removePlan = (index: number) => {
    if (plans.length <= 1) return
    planImages[index].previews.forEach(url => URL.revokeObjectURL(url))
    setPlans(plans.filter((_, i) => i !== index))
    setPlanImages(planImages.filter((_, i) => i !== index))
  }

  const handleAddImages = (index: number, newFiles: FileList | null) => {
    if (!newFiles) return
    const imgs = [...planImages]
    const current = imgs[index]
    const allowed = Array.from(newFiles).slice(0, 5 - current.files.length)
    imgs[index] = {
      files: [...current.files, ...allowed],
      previews: [...current.previews, ...allowed.map(f => URL.createObjectURL(f))],
    }
    setPlanImages(imgs)
  }

  const handleRemoveImage = (planIndex: number, imgIndex: number) => {
    const imgs = [...planImages]
    URL.revokeObjectURL(imgs[planIndex].previews[imgIndex])
    imgs[planIndex] = {
      files: imgs[planIndex].files.filter((_, i) => i !== imgIndex),
      previews: imgs[planIndex].previews.filter((_, i) => i !== imgIndex),
    }
    setPlanImages(imgs)
  }

  const updatePlan = (index: number, updates: Partial<CampaignPlan>) => {
    const newPlans = [...plans]
    newPlans[index] = { ...newPlans[index], ...updates }
    setPlans(newPlans)
  }

  const handleRace = () => {
    const payload: RacePayload = {
      market,
      product_line: productLine,
      audience_segment: audience,
      sort_by: sortBy,
      include_hypothesis: true,
      plans: plans.filter(p => p.name.trim() && p.theme),
      ...(seasonTag ? { season_tag: seasonTag } : {}),
    }
    
    saveRaceState({ payload })
    navigate('/running')
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-10 items-start">
      <div className="space-y-10">
        
        {/* Header / Positioning */}
        <section className="space-y-4">
          <h1 className="font-display text-4xl text-primary font-semibold">营销实验室</h1>
          <p className="text-muted-foreground text-lg leading-relaxed max-w-2xl text-balance">
            最多评估 5 个策略方向。引擎优先基于
            <strong className="text-primary font-medium mx-1">历史基线数据</strong>（经验漏斗数据）进行排序，
            辅以<span className="italic">模型假设</span>提供认知偏移与风险预警。
          </p>
        </section>

        {/* Global Context */}
        <section className="lab-card p-6 flex flex-wrap gap-8 items-end">
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">市场</label>
            <select
              value={market} onChange={e => setMarket(e.target.value)}
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
              value={productLine} onChange={e => setProductLine(e.target.value)}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="moodyplus">透明片（moodyPlus）</option>
              <option value="colored_lenses">彩片</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">优化目标</label>
            <select
              value={sortBy} onChange={e => setSortBy(e.target.value as 'roas_mean' | 'purchase_rate' | 'revenue_mean' | 'cvr_mean')}
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
              value={seasonTag} onChange={e => setSeasonTag(e.target.value)}
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

        {/* Plans Builder */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-2xl text-primary">策略方向</h2>
            <span className="text-sm text-muted-foreground">{plans.length} / 5</span>
          </div>

          <div className="space-y-4">
            {plans.map((plan, i) => (
              <div key={i} className="lab-card p-6 relative group border-l-4 border-l-border focus-within:border-l-primary transition-all">
                <button 
                  onClick={() => removePlan(i)}
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
                      onChange={e => updatePlan(i, { name: e.target.value })}
                      placeholder="例：春季科学种草"
                      className="lab-input text-lg font-display"
                    />
                  </div>
                  
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">认知主题</label>
                    <select
                      value={plan.theme} onChange={e => updatePlan(i, { theme: e.target.value })}
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
                      value={plan.platform} onChange={e => updatePlan(i, { platform: e.target.value })}
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
                      onChange={e => updatePlan(i, { budget: Number(e.target.value) })}
                      className="lab-input text-sm font-mono"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">渠道类型</label>
                    <select
                      value={plan.channel_family} onChange={e => updatePlan(i, { channel_family: e.target.value })}
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

                {/* Image Upload */}
                <div className="mt-6 space-y-2">
                  <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
                    素材图片（最多 5 张）
                  </label>
                  <div className="flex flex-wrap gap-3">
                    {planImages[i]?.previews.map((src, imgIdx) => (
                      <div key={imgIdx} className="relative w-20 h-20 rounded-sm overflow-hidden border border-border group/img">
                        <img src={src} alt={`素材 ${imgIdx + 1}`} className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={() => handleRemoveImage(i, imgIdx)}
                          className="absolute top-0.5 right-0.5 bg-black/60 text-white rounded-full p-0.5 opacity-0 group-hover/img:opacity-100 transition-opacity"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                    {(planImages[i]?.files.length ?? 0) < 5 && (
                      <button
                        type="button"
                        onClick={() => fileInputRefs.current[i]?.click()}
                        className="w-20 h-20 rounded-sm border border-dashed border-border flex flex-col items-center justify-center gap-1 text-muted-foreground hover:text-primary hover:border-primary transition-colors"
                      >
                        <ImagePlus className="h-5 w-5" />
                        <span className="text-[10px]">上传</span>
                      </button>
                    )}
                    <input
                      ref={el => { fileInputRefs.current[i] = el }}
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={e => { handleAddImages(i, e.target.files); e.target.value = '' }}
                    />
                  </div>
                </div>
              </div>
            ))}
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

      {/* Right Sidebar: Execution Summary & CTA */}
      <div className="sticky top-24 space-y-6">
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
                <span>模型假设不会覆盖经验排序，仅提供认知层面的参考。</span>
              </li>
            </ul>
          </div>

          <div className="pt-4 border-t border-border">
            <button 
              onClick={handleRace}
              disabled={plans.length === 0}
              className="lab-button lab-button-primary w-full h-12 text-base gap-2 group"
            >
              <Zap className="h-4 w-4 text-accent-foreground group-hover:animate-pulse" />
              开始评估
            </button>
            <p className="text-[10px] text-center text-muted-foreground mt-3 uppercase tracking-wider">
              预计需要约 15 秒计算时间
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
