import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRaceState, type RaceResult, type RankingEntry, type VisualProfile, clearRaceState } from '../lib/api'
import { ChevronDown, ChevronUp, AlertTriangle, Activity, Beaker, Snowflake, Lightbulb, Eye, ImageIcon } from 'lucide-react'
import { RadarScoreChart } from '../components/RadarScoreChart'
import { PercentileBar } from '../components/PercentileBar'
import { DiagnosticsPanel } from '../components/DiagnosticsPanel'

export function ResultPage() {
  const navigate = useNavigate()
  const [result] = useState<RaceResult | null>(() => {
    const state = getRaceState()
    return state?.result || null
  })
  const [expandedPlan, setExpandedPlan] = useState<number | null>(null)

  useEffect(() => {
    if (!result) {
      navigate('/')
    }
  }, [navigate, result])

  if (!result) return null

  const { observed_baseline, model_hypothesis, visual_analysis } = result
  const ranking = observed_baseline.ranking
  const topEntry = ranking[0]
  const visualProfiles = visual_analysis?.profiles ?? {}

  return (
    <div className="space-y-12 pb-20 animate-in fade-in duration-700">

      {/* Header Summary */}
      <section className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl text-primary font-semibold mb-2">评估结果</h1>
            <p className="text-muted-foreground max-w-2xl text-balance">
              按 <strong className="text-primary font-medium">{observed_baseline.sort_by.replace(/_/g, ' ').toUpperCase()}</strong> 评估策略方向。
              {topEntry && (
                <>
                  {' '}<span className="text-primary font-medium">{topEntry.plan.name || `方案 #${topEntry.rank}`}</span> 为最优策略
                  {topEntry.data_sufficient ? '。' : '（历史数据有限）。'}
                </>
              )}
            </p>
          </div>
          <button
            onClick={() => { clearRaceState(); navigate('/') }}
            className="lab-button lab-button-outline"
          >
            新评估
          </button>
        </div>

        {/* Recommendation */}
        {observed_baseline.recommendation && (
          <div className="lab-card p-5 flex gap-4 items-start bg-primary/5 border-primary/20">
            <AlertTriangle className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div>
              <h3 className="text-xs uppercase tracking-wider font-bold text-primary mb-2">策略建议</h3>
              <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{observed_baseline.recommendation}</p>
            </div>
          </div>
        )}
      </section>

      {/* Side-by-Side Comparison */}
      <section className="space-y-6">
        <h2 className="font-display text-2xl text-primary border-b border-border pb-4">方案对比</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ranking.map((entry: RankingEntry) => (
            <div key={entry.rank} className="lab-card p-5 space-y-3">
              {/* Campaign name + rank badge */}
              <div className="flex items-center gap-3">
                <div className="flex flex-col items-center justify-center w-8 h-8 rounded-sm bg-primary text-primary-foreground font-display text-sm font-semibold shrink-0">
                  {entry.rank}
                </div>
                <h3 className="font-semibold text-base">{entry.plan.name || `方案 #${entry.rank}`}</h3>
              </div>

              {/* Thumbnail images */}
              {entry.plan.image_paths && entry.plan.image_paths.length > 0 && (
                <div className="flex gap-2 overflow-x-auto">
                  {entry.plan.image_paths.slice(0, 3).map((img, i) => (
                    <img key={i} src={img} alt={`素材 ${i + 1}`} className="w-16 h-16 rounded-sm border border-border object-cover bg-background shrink-0" />
                  ))}
                </div>
              )}

              {/* Score summary */}
              <div className="flex items-center gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground text-xs uppercase tracking-wider">{observed_baseline.sort_by.replace(/_/g, ' ')}</span>
                  <div className="font-mono text-lg font-medium">{entry.score.toFixed(2)}</div>
                </div>
                {entry.observed_baseline.roas_mean != null && (
                  <div>
                    <span className="text-muted-foreground text-xs uppercase tracking-wider">ROAS</span>
                    <div className="font-mono text-lg">{entry.observed_baseline.roas_mean.toFixed(2)}</div>
                  </div>
                )}
                {entry.observed_baseline.cvr_mean != null && (
                  <div>
                    <span className="text-muted-foreground text-xs uppercase tracking-wider">CVR</span>
                    <div className="font-mono text-lg">{(entry.observed_baseline.cvr_mean * 100).toFixed(1)}%</div>
                  </div>
                )}
              </div>

              {/* Percentile bar */}
              {entry.observed_baseline.percentile != null && (
                <PercentileBar percentile={entry.observed_baseline.percentile} />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Radar Chart - Visual Score Dimensions */}
      {(() => {
        // Build dimension data from visual profiles
        const radarCampaigns = ranking
          .filter((entry: RankingEntry) => {
            const planKey = entry.plan.id || entry.plan.name || ''
            return visualProfiles[planKey]
          })
          .map((entry: RankingEntry) => {
            const planKey = entry.plan.id || entry.plan.name || ''
            const vp = visualProfiles[planKey]
            const dimensions: Record<string, number> = {}
            if (vp.trust_signal_strength != null) dimensions.trust_signal = vp.trust_signal_strength
            if (vp.product_visibility != null) dimensions.product_visibility = vp.product_visibility
            if (vp.promo_intensity != null) dimensions.promo_intensity = vp.promo_intensity
            if (vp.text_density != null) dimensions.text_density = vp.text_density
            if (vp.consistency_score != null) dimensions.consistency = vp.consistency_score
            return { name: entry.plan.name || `方案 #${entry.rank}`, dimensions }
          })

        if (radarCampaigns.length === 0) return null

        return (
          <section className="space-y-6">
            <RadarScoreChart
              campaigns={radarCampaigns}
              dimensionLabels={{
                trust_signal: '信任信号',
                product_visibility: '产品可见度',
                promo_intensity: '促销感',
                text_density: '文字密度',
                consistency: '素材一致性',
              }}
            />
          </section>
        )
      })()}

      {/* Rankings List */}
      <section className="space-y-6">
        <h2 className="font-display text-2xl text-primary border-b border-border pb-4">评估轨道</h2>

        <div className="space-y-4">
          {ranking.map((entry: RankingEntry) => {
            const hypothesis = model_hypothesis?.plans.find(
              h => h.plan.name === entry.plan.name || h.plan.theme === entry.plan.theme
            )
            const isExpanded = expandedPlan === entry.rank

            return (
              <div key={entry.rank} className="lab-card overflow-hidden transition-all duration-300">

                {/* Header Row */}
                <div
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  aria-label={`${entry.plan.name || `Plan #${entry.rank}`} — rank ${entry.rank}`}
                  className={`p-6 cursor-pointer flex flex-col md:flex-row gap-6 items-start md:items-center justify-between hover:bg-black/5 transition-colors ${isExpanded ? 'bg-black/5' : ''}`}
                  onClick={() => setExpandedPlan(isExpanded ? null : entry.rank)}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpandedPlan(isExpanded ? null : entry.rank) } }}
                >
                  <div className="flex items-center gap-6">
                    <div className="flex flex-col items-center justify-center w-10 h-10 rounded-sm bg-primary text-primary-foreground font-display text-xl font-semibold shrink-0">
                      {entry.rank}
                    </div>
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-lg font-semibold">{entry.plan.name || `方案 #${entry.rank}`}</h3>
                        {entry.rank === 1 && <span className="baseline-tag bg-accent text-accent-foreground">最优选择</span>}
                        {!entry.data_sufficient && <span className="hypothesis-tag">数据稀疏</span>}
                        {entry.visual_adjustment?.applied && (
                          <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-sm bg-violet-100 text-violet-700 border border-violet-200">
                            <Eye className="h-3 w-3" />
                            图片影响排序
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                        <span>{(entry.plan.theme || '').replace(/_/g, ' ').toUpperCase()}</span>
                        <span>&bull;</span>
                        <span>{(entry.plan.platform || '').toUpperCase()}</span>
                        <span>&bull;</span>
                        <span className="capitalize">{entry.observed_baseline.match_quality}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-8 w-full md:w-auto">
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{observed_baseline.sort_by.replace(/_/g, ' ')}</div>
                      <div className="font-mono text-lg font-medium">{entry.score.toFixed(2)}</div>
                    </div>
                    <div className="text-right hidden sm:block">
                      <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">样本量</div>
                      <div className="font-mono text-lg">{entry.observed_baseline.sample_size}</div>
                    </div>
                    <button className="p-2 text-muted-foreground hover:text-primary">
                      {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Detail View */}
                {isExpanded && (
                  <div className="border-t border-border bg-[#FDFCFB]">

                    {/* Track 1: Observed Baseline */}
                    <div className="p-6 border-b border-border/50 space-y-6">
                      <div className="flex items-center gap-2 mb-4">
                        <Activity className="h-4 w-4 text-primary" />
                        <h4 className="font-semibold text-sm uppercase tracking-widest text-primary">轨道 1：历史基线数据</h4>
                        <span className="baseline-tag ml-2">主要依据</span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        {entry.plan.image_paths && entry.plan.image_paths.length > 0 && (
                          <div className="col-span-2 md:col-span-4 space-y-3">
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                              素材回看
                            </div>
                            <div className="flex flex-wrap gap-3">
                              {entry.plan.image_paths.map((imagePath, imageIndex) => (
                                <img
                                  key={`${entry.rank}-${imageIndex}`}
                                  src={imagePath}
                                  alt={`${entry.plan.name || `Plan #${entry.rank}`} 素材 ${imageIndex + 1}`}
                                  className="w-20 h-20 rounded-sm border border-border object-cover bg-background"
                                />
                              ))}
                            </div>
                          </div>
                        )}
                        {entry.observed_baseline.roas_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">ROAS（均值）</div>
                            <div className="font-mono text-xl">{entry.observed_baseline.roas_mean.toFixed(2)}</div>
                          </div>
                        )}
                        {entry.observed_baseline.cvr_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">CVR（均值）</div>
                            <div className="font-mono text-xl">{(entry.observed_baseline.cvr_mean * 100).toFixed(1)}%</div>
                          </div>
                        )}
                        {entry.observed_baseline.purchase_rate != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">购买率</div>
                            <div className="font-mono text-xl">{(entry.observed_baseline.purchase_rate * 100).toFixed(1)}%</div>
                          </div>
                        )}
                        {entry.observed_baseline.revenue_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">收入（均值）</div>
                            <div className="font-mono text-xl">{entry.observed_baseline.revenue_mean.toLocaleString()}</div>
                          </div>
                        )}
                        {entry.observed_baseline.sessions_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">会话数（均值）</div>
                            <div className="font-mono text-xl">{Math.round(entry.observed_baseline.sessions_mean).toLocaleString()}</div>
                          </div>
                        )}
                        {entry.observed_baseline.aov_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">AOV（均值）</div>
                            <div className="font-mono text-xl">{entry.observed_baseline.aov_mean.toFixed(0)}</div>
                          </div>
                        )}
                        {entry.observed_baseline.cpa != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">CPA</div>
                            <div className="font-mono text-xl">{entry.observed_baseline.cpa.toFixed(0)}</div>
                          </div>
                        )}
                        <div>
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">匹配质量</div>
                          <div className="font-mono text-sm mt-1 uppercase bg-secondary/50 inline-block px-2 py-1 rounded-sm text-secondary-foreground">
                            {entry.observed_baseline.match_quality}
                          </div>
                        </div>
                      </div>

                      {entry.observed_baseline.match_dimensions.length > 0 && (
                        <div className="pt-4">
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">匹配维度</div>
                          <div className="flex flex-wrap gap-2">
                            {entry.observed_baseline.match_dimensions.map(dim => (
                              <span key={dim} className="text-xs font-mono bg-secondary/30 px-2 py-1 rounded-sm">
                                {dim}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Drift indicators */}
                      {entry.observed_baseline.drift_30d && (
                        <div className="pt-4 border-t border-border/30">
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">近期趋势（30天 vs 全量）</div>
                          <div className="flex flex-wrap gap-4">
                            {Object.entries(entry.observed_baseline.drift_30d).map(([metric, drift]) => (
                              <div key={metric} className="text-xs font-mono">
                                <span className="text-muted-foreground">{metric}: </span>
                                <span className={drift > 0 ? 'text-green-600' : drift < 0 ? 'text-red-600' : ''}>
                                  {drift > 0 ? '+' : ''}{(drift * 100).toFixed(0)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Seasonal drift */}
                      {entry.observed_baseline.seasonal_drift && (
                        <div className="pt-4 border-t border-border/30">
                          <div className="flex items-center gap-2 mb-2">
                            <Snowflake className="h-3 w-3 text-primary" />
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                              季节：{entry.observed_baseline.seasonal_drift.current_season}
                              <span className="ml-2 text-muted-foreground/70">
                                （{entry.observed_baseline.seasonal_drift.sample_in_season} 季节内 / {entry.observed_baseline.seasonal_drift.sample_regular} 常规）
                              </span>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-4">
                            {entry.observed_baseline.seasonal_drift.season_vs_regular_roas != null && (
                              <div className="text-xs font-mono">
                                <span className="text-muted-foreground">ROAS vs 常规：</span>
                                <span className={entry.observed_baseline.seasonal_drift.season_vs_regular_roas > 0 ? 'text-green-600' : entry.observed_baseline.seasonal_drift.season_vs_regular_roas < 0 ? 'text-red-600' : ''}>
                                  {entry.observed_baseline.seasonal_drift.season_vs_regular_roas > 0 ? '+' : ''}{entry.observed_baseline.seasonal_drift.season_vs_regular_roas.toFixed(2)}
                                </span>
                              </div>
                            )}
                            {entry.observed_baseline.seasonal_drift.season_vs_regular_cvr != null && (
                              <div className="text-xs font-mono">
                                <span className="text-muted-foreground">CVR vs 常规：</span>
                                <span className={entry.observed_baseline.seasonal_drift.season_vs_regular_cvr > 0 ? 'text-green-600' : entry.observed_baseline.seasonal_drift.season_vs_regular_cvr < 0 ? 'text-red-600' : ''}>
                                  {entry.observed_baseline.seasonal_drift.season_vs_regular_cvr > 0 ? '+' : ''}{(entry.observed_baseline.seasonal_drift.season_vs_regular_cvr * 100).toFixed(1)}%
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Cold start hint */}
                      {entry.observed_baseline.cold_start_hint && (
                        <div className="pt-4 border-t border-border/30">
                          <div className="flex items-center gap-2 mb-2">
                            <Lightbulb className="h-3 w-3 text-amber-500" />
                            <div className="text-[10px] text-amber-600 uppercase tracking-wider font-semibold">
                              {entry.observed_baseline.cold_start_hint.type === 'cross_category' ? '跨品类迁移' : '分布估计'}
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground mb-3">{entry.observed_baseline.cold_start_hint.note}</p>
                          {entry.observed_baseline.cold_start_hint.type === 'cross_category' && entry.observed_baseline.cold_start_hint.source_product_lines && (
                            <div className="text-xs font-mono text-muted-foreground">
                              来源：{entry.observed_baseline.cold_start_hint.source_product_lines.join(', ')} | 折扣：{((entry.observed_baseline.cold_start_hint.discount_applied ?? 1) * 100).toFixed(0)}%
                            </div>
                          )}
                          {entry.observed_baseline.cold_start_hint.type === 'distribution_estimate' && (
                            <div className="grid grid-cols-3 gap-4">
                              {entry.observed_baseline.cold_start_hint.roas_range && (
                                <div className="text-xs">
                                  <div className="text-muted-foreground mb-1">ROAS 范围</div>
                                  <div className="font-mono">
                                    P25: {entry.observed_baseline.cold_start_hint.roas_range.p25} / P50: {entry.observed_baseline.cold_start_hint.roas_range.p50} / P75: {entry.observed_baseline.cold_start_hint.roas_range.p75}
                                  </div>
                                </div>
                              )}
                              {entry.observed_baseline.cold_start_hint.cvr_range && (
                                <div className="text-xs">
                                  <div className="text-muted-foreground mb-1">CVR 范围</div>
                                  <div className="font-mono">
                                    P25: {(entry.observed_baseline.cold_start_hint.cvr_range.p25 * 100).toFixed(1)}% / P50: {(entry.observed_baseline.cold_start_hint.cvr_range.p50 * 100).toFixed(1)}% / P75: {(entry.observed_baseline.cold_start_hint.cvr_range.p75 * 100).toFixed(1)}%
                                  </div>
                                </div>
                              )}
                              {entry.observed_baseline.cold_start_hint.revenue_range && (
                                <div className="text-xs">
                                  <div className="text-muted-foreground mb-1">收入范围</div>
                                  <div className="font-mono">
                                    P25: {entry.observed_baseline.cold_start_hint.revenue_range.p25.toLocaleString()} / P50: {entry.observed_baseline.cold_start_hint.revenue_range.p50.toLocaleString()} / P75: {entry.observed_baseline.cold_start_hint.revenue_range.p75.toLocaleString()}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Visual Analysis Section */}
                    {(() => {
                      const planKey = entry.plan.id || entry.plan.name || ''
                      const vp: VisualProfile | undefined = visualProfiles[planKey]
                      const va = entry.visual_adjustment
                      if (!vp && !va?.applied) return null

                      return (
                        <div className="p-6 border-b border-border/50 space-y-5 bg-violet-50/30">
                          <div className="flex items-center gap-2 mb-4">
                            <ImageIcon className="h-4 w-4 text-violet-600" />
                            <h4 className="font-semibold text-sm uppercase tracking-widest text-violet-700">素材内容分析</h4>
                            {va?.applied && (
                              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-sm bg-violet-100 text-violet-700 border border-violet-200 ml-2">
                                已参与排序
                              </span>
                            )}
                          </div>

                          {vp && (
                            <>
                              {/* Key visual signals */}
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {vp.creative_style && (
                                  <div>
                                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">素材风格</div>
                                    <div className="font-mono text-sm capitalize">{vp.creative_style}</div>
                                  </div>
                                )}
                                {vp.aesthetic_tone && (
                                  <div>
                                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">审美调性</div>
                                    <div className="font-mono text-sm capitalize">{vp.aesthetic_tone}</div>
                                  </div>
                                )}
                                {vp.visual_claim_focus && (
                                  <div>
                                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">卖点方向</div>
                                    <div className="font-mono text-sm capitalize">{vp.visual_claim_focus.replace(/_/g, ' ')}</div>
                                  </div>
                                )}
                                {vp.premium_vs_mass && (
                                  <div>
                                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">定位</div>
                                    <div className="font-mono text-sm capitalize">{vp.premium_vs_mass}</div>
                                  </div>
                                )}
                              </div>

                              {/* Numeric gauges */}
                              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
                                {vp.trust_signal_strength != null && (
                                  <div className="bg-background border border-border p-2 text-center rounded-sm">
                                    <div className="text-[10px] text-muted-foreground truncate mb-1">信任信号</div>
                                    <div className="font-mono text-sm font-medium">{vp.trust_signal_strength}/10</div>
                                  </div>
                                )}
                                {vp.product_visibility != null && (
                                  <div className="bg-background border border-border p-2 text-center rounded-sm">
                                    <div className="text-[10px] text-muted-foreground truncate mb-1">产品可见度</div>
                                    <div className="font-mono text-sm font-medium">{vp.product_visibility}/10</div>
                                  </div>
                                )}
                                {vp.promo_intensity != null && (
                                  <div className="bg-background border border-border p-2 text-center rounded-sm">
                                    <div className="text-[10px] text-muted-foreground truncate mb-1">促销感</div>
                                    <div className="font-mono text-sm font-medium">{vp.promo_intensity}/10</div>
                                  </div>
                                )}
                                {vp.text_density != null && (
                                  <div className="bg-background border border-border p-2 text-center rounded-sm">
                                    <div className="text-[10px] text-muted-foreground truncate mb-1">文字密度</div>
                                    <div className="font-mono text-sm font-medium">{vp.text_density}/10</div>
                                  </div>
                                )}
                                {vp.consistency_score != null && vp.image_count != null && vp.image_count > 1 && (
                                  <div className="bg-background border border-border p-2 text-center rounded-sm">
                                    <div className="text-[10px] text-muted-foreground truncate mb-1">素材一致性</div>
                                    <div className="font-mono text-sm font-medium">{vp.consistency_score}/10</div>
                                  </div>
                                )}
                              </div>

                              {/* Hooks and risks */}
                              <div className="flex flex-wrap gap-6">
                                {vp.visual_hooks && vp.visual_hooks.length > 0 && (
                                  <div>
                                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">视觉钩子</div>
                                    <div className="flex flex-wrap gap-2">
                                      {vp.visual_hooks.map((hook, i) => (
                                        <span key={i} className="text-xs font-mono bg-green-50 text-green-700 border border-green-200 px-2 py-1 rounded-sm">
                                          {hook}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {vp.visual_risks && vp.visual_risks.length > 0 && (
                                  <div>
                                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">视觉风险</div>
                                    <div className="flex flex-wrap gap-2">
                                      {vp.visual_risks.map((risk, i) => (
                                        <span key={i} className="text-xs font-mono bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-sm">
                                          {risk}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Summary */}
                              {vp.summary && (
                                <p className="text-sm text-muted-foreground leading-relaxed">{vp.summary}</p>
                              )}
                            </>
                          )}

                          {/* Visual adjustment explanation */}
                          {va?.applied && va.score_delta != null && (
                            <div className="pt-4 border-t border-violet-200/50">
                              <div className="flex items-center gap-2 mb-2">
                                <Eye className="h-3 w-3 text-violet-600" />
                                <div className="text-[10px] text-violet-700 uppercase tracking-wider font-semibold">排序调整</div>
                              </div>
                              <div className="flex flex-wrap gap-4 text-xs font-mono">
                                <span className="text-muted-foreground">
                                  视觉质量分: <strong className="text-foreground">{va.visual_score?.toFixed(3)}</strong>
                                </span>
                                <span className="text-muted-foreground">
                                  分数调整: <strong className={va.score_delta > 0 ? 'text-green-600' : va.score_delta < 0 ? 'text-red-600' : 'text-foreground'}>
                                    {va.score_delta > 0 ? '+' : ''}{va.score_delta.toFixed(4)}
                                  </strong>
                                </span>
                                <span className="text-muted-foreground">
                                  触发原因: {va.reason === 'close_baseline_scores' ? '基线分数接近' : va.reason === 'all_cold_start' ? '全部冷启动' : va.reason}
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })()}

                    {/* Visual Diagnostics */}
                    {(() => {
                      const planKey = entry.plan.id || entry.plan.name || ''
                      const vp = visualProfiles[planKey]
                      if (!vp?.diagnostics) return null
                      return (
                        <div className="p-6 border-b border-border/50">
                          <DiagnosticsPanel diagnostics={vp.diagnostics} />
                        </div>
                      )
                    })()}

                    {/* Track 2: Model Hypothesis */}
                    {hypothesis && !hypothesis.error && hypothesis.predicted_delta && (
                      <div className="p-6 bg-muted/20 space-y-6">
                        <div className="flex items-center gap-2 mb-4">
                          <Beaker className="h-4 w-4 text-muted-foreground" />
                          <h4 className="font-semibold text-sm uppercase tracking-widest text-muted-foreground">轨道 2：认知模型假设</h4>
                          <span className="hypothesis-tag ml-2">实验性参考</span>
                        </div>

                        <p className="text-sm text-muted-foreground leading-relaxed max-w-3xl">
                          {hypothesis.reasoning}
                        </p>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-2">
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">模型置信度</div>
                            <div className="font-mono text-sm">{((hypothesis.confidence || 0) * 100).toFixed(0)}%</div>
                          </div>
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">相似干预</div>
                            <div className="font-mono text-sm">找到 {hypothesis.similar_interventions || 0} 条</div>
                          </div>
                        </div>

                        <div className="pt-2 border-t border-muted-foreground/10">
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">预测认知偏移（7天）</div>
                          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                            {Object.entries(hypothesis.predicted_delta).map(([dim, val]) => (
                              <div key={dim} className="bg-background border border-border p-2 text-center rounded-sm">
                                <div className="text-[10px] text-muted-foreground truncate mb-1" title={dim}>
                                  {dim.replace(/_/g, ' ')}
                                </div>
                                <div className={`font-mono text-xs font-medium ${val > 0 ? 'text-green-600' : val < 0 ? 'text-red-600' : ''}`}>
                                  {val > 0 ? '+' : ''}{val.toFixed(2)}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {hypothesis?.error && (
                      <div className="p-6 bg-muted/20">
                        <p className="text-sm text-muted-foreground">轨道 2 不可用：{hypothesis.error}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </section>

    </div>
  )
}
