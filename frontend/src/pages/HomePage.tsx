import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, Zap, AlertCircle } from 'lucide-react'
import { type RacePayload, type CampaignPlan, saveRaceState } from '../lib/api'

const DEFAULT_PLAN: CampaignPlan = {
  name: '',
  theme: 'science_credibility',
  platform: 'redbook',
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
    { ...DEFAULT_PLAN, name: 'Plan B', theme: 'comfort_beauty', platform: 'douyin' },
  ])

  const addPlan = () => {
    if (plans.length >= 5) return
    setPlans([...plans, { ...DEFAULT_PLAN, name: `Plan ${String.fromCharCode(65 + plans.length)}` }])
  }

  const removePlan = (index: number) => {
    if (plans.length <= 1) return
    setPlans(plans.filter((_, i) => i !== index))
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
          <h1 className="font-display text-4xl text-primary font-semibold">Campaign Lab</h1>
          <p className="text-muted-foreground text-lg leading-relaxed max-w-2xl text-balance">
            Evaluate up to 5 strategic campaign directions. The engine resolves rankings primarily through 
            <strong className="text-primary font-medium mx-1">Observed Historical Baselines</strong> (empirical funnel data), 
            supplemented by <span className="italic">Model Hypothesis</span> for perception shifts and secondary risk flagging.
          </p>
        </section>

        {/* Global Context */}
        <section className="lab-card p-6 flex flex-wrap gap-8 items-end">
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">Market Context</label>
            <select 
              value={market} onChange={e => setMarket(e.target.value)}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="cn">China (Mainland)</option>
              <option value="us">United States</option>
              <option value="sea">Southeast Asia</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">Product Line</label>
            <select 
              value={productLine} onChange={e => setProductLine(e.target.value)}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="moodyplus">Moody Plus (Core)</option>
              <option value="colored_lenses">Colored Lenses</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">Optimization Target</label>
            <select
              value={sortBy} onChange={e => setSortBy(e.target.value as 'roas_mean' | 'purchase_rate' | 'revenue_mean' | 'cvr_mean')}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="roas_mean">ROAS (Mean)</option>
              <option value="revenue_mean">Revenue Potential</option>
              <option value="purchase_rate">Conversion Rate</option>
            </select>
          </div>
          <div className="space-y-1.5 flex-1 min-w-[120px]">
            <label className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">Season Context</label>
            <select
              value={seasonTag} onChange={e => setSeasonTag(e.target.value)}
              className="lab-input font-medium pb-2 cursor-pointer"
            >
              <option value="">Regular (No Season)</option>
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
            <h2 className="font-display text-2xl text-primary">Strategic Directions</h2>
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
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">Plan Designation</label>
                    <input 
                      type="text" 
                      value={plan.name} 
                      onChange={e => updatePlan(i, { name: e.target.value })}
                      placeholder="e.g., Spring Science Seed"
                      className="lab-input text-lg font-display"
                    />
                  </div>
                  
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">Cognitive Theme</label>
                    <select 
                      value={plan.theme} onChange={e => updatePlan(i, { theme: e.target.value })}
                      className="lab-input text-sm"
                    >
                      <option value="science_credibility">Science & Credibility</option>
                      <option value="comfort_beauty">Comfort & Beauty</option>
                      <option value="aesthetic">Aesthetic & Visual</option>
                      <option value="price">Price & Value</option>
                      <option value="social">Social Proof / KOL</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">Primary Platform</label>
                    <select 
                      value={plan.platform} onChange={e => updatePlan(i, { platform: e.target.value })}
                      className="lab-input text-sm"
                    >
                      <option value="redbook">Redbook (Xiaohongshu)</option>
                      <option value="douyin">Douyin</option>
                      <option value="tmall">Tmall ecosystem</option>
                      <option value="bilibili">Bilibili</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">Budget Allocation (CNY)</label>
                    <input 
                      type="number" 
                      value={plan.budget} 
                      onChange={e => updatePlan(i, { budget: Number(e.target.value) })}
                      className="lab-input text-sm font-mono"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">Channel Family</label>
                    <select 
                      value={plan.channel_family} onChange={e => updatePlan(i, { channel_family: e.target.value })}
                      className="lab-input text-sm"
                    >
                      <option value="social_seed">Social Seeding / KOC</option>
                      <option value="short_video">Short Video</option>
                      <option value="longform_content">Longform Content</option>
                      <option value="marketplace">Marketplace / E-Commerce</option>
                      <option value="influencer">Influencer / KOL</option>
                      <option value="search">Search Ads</option>
                    </select>
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
              <Plus className="h-4 w-4" /> Add Strategic Direction
            </button>
          )}
        </section>

      </div>

      {/* Right Sidebar: Execution Summary & CTA */}
      <div className="sticky top-24 space-y-6">
        <div className="lab-card p-5 space-y-5 bg-card/50">
          <div>
            <h3 className="text-xs uppercase tracking-wider font-bold text-primary mb-3">Evaluation Matrix</h3>
            <ul className="space-y-3 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <span className="baseline-tag shrink-0 mt-0.5">Tier 1</span>
                <span>Historical Funnel Baseline & Empirical Comparables</span>
              </li>
              <li className="flex gap-2">
                <span className="hypothesis-tag shrink-0 mt-0.5">Tier 2</span>
                <span>Perception Model Hypothesis (experimental)</span>
              </li>
              <li className="flex gap-2 text-xs">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-accent" />
                <span>Model hypothesis does not override empirical ranking. It provides perception context only.</span>
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
              Initialize Race
            </button>
            <p className="text-[10px] text-center text-muted-foreground mt-3 uppercase tracking-wider">
              Requires ~15 seconds compute time
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
