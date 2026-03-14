import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRaceState, type RaceResult, type RankingEntry, clearRaceState } from '../lib/api'
import { ChevronDown, ChevronUp, AlertTriangle, Activity, Beaker } from 'lucide-react'

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

  const { observed_baseline, model_hypothesis } = result
  const ranking = observed_baseline.ranking
  const topEntry = ranking[0]

  return (
    <div className="space-y-12 pb-20 animate-in fade-in duration-700">

      {/* Header Summary */}
      <section className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl text-primary font-semibold mb-2">Race Resolution</h1>
            <p className="text-muted-foreground max-w-2xl text-balance">
              Strategic directions evaluated by <strong className="text-primary font-medium">{observed_baseline.sort_by.replace(/_/g, ' ').toUpperCase()}</strong>.
              {topEntry && (
                <>
                  {' '}<span className="text-primary font-medium">{topEntry.plan.name || `Plan #${topEntry.rank}`}</span> emerges as the dominant strategy
                  {topEntry.data_sufficient ? '.' : ' (limited historical evidence).'}
                </>
              )}
            </p>
          </div>
          <button
            onClick={() => { clearRaceState(); navigate('/') }}
            className="lab-button lab-button-outline"
          >
            New Race
          </button>
        </div>

        {/* Recommendation */}
        {observed_baseline.recommendation && (
          <div className="lab-card p-5 flex gap-4 items-start bg-primary/5 border-primary/20">
            <AlertTriangle className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div>
              <h3 className="text-xs uppercase tracking-wider font-bold text-primary mb-2">Strategic Recommendation</h3>
              <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{observed_baseline.recommendation}</p>
            </div>
          </div>
        )}
      </section>

      {/* Rankings List */}
      <section className="space-y-6">
        <h2 className="font-display text-2xl text-primary border-b border-border pb-4">Evaluation Tracks</h2>

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
                        <h3 className="text-lg font-semibold">{entry.plan.name || `Plan #${entry.rank}`}</h3>
                        {entry.rank === 1 && <span className="baseline-tag bg-accent text-accent-foreground">Top Choice</span>}
                        {!entry.data_sufficient && <span className="hypothesis-tag">Sparse Data</span>}
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
                      <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Sample Size</div>
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
                        <h4 className="font-semibold text-sm uppercase tracking-widest text-primary">Track 1: Observed Historical Baseline</h4>
                        <span className="baseline-tag ml-2">Primary Driver</span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        {entry.observed_baseline.roas_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">ROAS (Mean)</div>
                            <div className="font-mono text-xl">{entry.observed_baseline.roas_mean.toFixed(2)}</div>
                          </div>
                        )}
                        {entry.observed_baseline.cvr_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">CVR (Mean)</div>
                            <div className="font-mono text-xl">{(entry.observed_baseline.cvr_mean * 100).toFixed(1)}%</div>
                          </div>
                        )}
                        {entry.observed_baseline.purchase_rate != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Purchase Rate</div>
                            <div className="font-mono text-xl">{(entry.observed_baseline.purchase_rate * 100).toFixed(1)}%</div>
                          </div>
                        )}
                        {entry.observed_baseline.revenue_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Revenue (Mean)</div>
                            <div className="font-mono text-xl">{entry.observed_baseline.revenue_mean.toLocaleString()}</div>
                          </div>
                        )}
                        {entry.observed_baseline.sessions_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Sessions (Mean)</div>
                            <div className="font-mono text-xl">{Math.round(entry.observed_baseline.sessions_mean).toLocaleString()}</div>
                          </div>
                        )}
                        {entry.observed_baseline.aov_mean != null && (
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">AOV (Mean)</div>
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
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Match Quality</div>
                          <div className="font-mono text-sm mt-1 uppercase bg-secondary/50 inline-block px-2 py-1 rounded-sm text-secondary-foreground">
                            {entry.observed_baseline.match_quality}
                          </div>
                        </div>
                      </div>

                      {entry.observed_baseline.match_dimensions.length > 0 && (
                        <div className="pt-4">
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Matched Dimensions</div>
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
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Recent Trend (30d vs All-Time)</div>
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
                    </div>

                    {/* Track 2: Model Hypothesis */}
                    {hypothesis && !hypothesis.error && hypothesis.predicted_delta && (
                      <div className="p-6 bg-muted/20 space-y-6">
                        <div className="flex items-center gap-2 mb-4">
                          <Beaker className="h-4 w-4 text-muted-foreground" />
                          <h4 className="font-semibold text-sm uppercase tracking-widest text-muted-foreground">Track 2: Perception Model Hypothesis</h4>
                          <span className="hypothesis-tag ml-2">Experimental Context</span>
                        </div>

                        <p className="text-sm text-muted-foreground leading-relaxed max-w-3xl">
                          {hypothesis.reasoning}
                        </p>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-2">
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Model Confidence</div>
                            <div className="font-mono text-sm">{((hypothesis.confidence || 0) * 100).toFixed(0)}%</div>
                          </div>
                          <div>
                            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Similar Interventions</div>
                            <div className="font-mono text-sm">{hypothesis.similar_interventions || 0} found</div>
                          </div>
                        </div>

                        <div className="pt-2 border-t border-muted-foreground/10">
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">Predicted Perception Shifts (7D)</div>
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
                        <p className="text-sm text-muted-foreground">Track 2 unavailable: {hypothesis.error}</p>
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
