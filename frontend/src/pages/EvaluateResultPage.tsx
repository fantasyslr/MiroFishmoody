import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getEvaluateState,
  clearEvaluateState,
  type EvaluateResult,
  type EvalRanking,
  type EvalPanelScore,
  type EvalPairwiseResult,
  type EvalScoreboard,
} from '../lib/api'
import { User, Trophy, AlertTriangle, ChevronDown, ChevronUp, BarChart3, Users, GitCompare, Download, Loader2 } from 'lucide-react'
import { captureElementAsImage, captureElementAsPDF } from '../lib/exportUtils'
import { RadarScoreChart } from '../components/RadarScoreChart'
import { DiagnosticsPanel } from '../components/DiagnosticsPanel'
import type { VisualDiagnostics } from '../lib/api'

type TabKey = 'ranking' | 'persona' | 'pairwise'

const VERDICT_STYLE: Record<string, { label: string; bg: string; text: string }> = {
  ship: { label: '上线', bg: 'bg-green-100', text: 'text-green-700' },
  revise: { label: '修改', bg: 'bg-amber-100', text: 'text-amber-700' },
  kill: { label: '淘汰', bg: 'bg-red-100', text: 'text-red-700' },
}

const PERSONA_COLORS = [
  'bg-blue-100 text-blue-700',
  'bg-purple-100 text-purple-700',
  'bg-teal-100 text-teal-700',
  'bg-rose-100 text-rose-700',
  'bg-orange-100 text-orange-700',
]

const DIMENSION_LABELS: Record<string, string> = {
  thumb_stop: '停留吸引力',
  clarity: '信息清晰度',
  trust: '信任感',
  conversion_readiness: '转化就绪度',
  claim_risk: '声称风险',
}

export function EvaluateResultPage() {
  const navigate = useNavigate()
  const [result] = useState<EvaluateResult | null>(() => {
    const state = getEvaluateState()
    return state?.result || null
  })
  const [activeTab, setActiveTab] = useState<TabKey>('ranking')
  const [exporting, setExporting] = useState<'pdf' | 'image' | null>(null)
  const exportRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!result) {
      navigate('/')
    }
  }, [navigate, result])

  if (!result) return null

  const rankings = [...result.rankings].sort((a, b) => a.rank - b.rank)
  const scoreboard = result.scoreboard

  // Build campaign name map from rankings
  const campaignNameMap: Record<string, string> = {}
  for (const r of rankings) {
    campaignNameMap[r.campaign_id] = r.campaign_name
  }

  // Build diagnostics map from backend visual_diagnostics
  const diagnosticsMap: Record<string, VisualDiagnostics> = result.visual_diagnostics ?? {}

  const handleExportPDF = async () => {
    if (!exportRef.current || exporting) return
    setExporting('pdf')
    try {
      const topName = rankings[0]?.campaign_name || '评审'
      const date = new Date().toLocaleDateString('zh-CN')
      const title = `MiroFishmoody 推演报告 — ${topName} — ${date}`
      const filename = `${topName}_推演报告_${date}`
      await captureElementAsPDF(exportRef.current, filename, title)
    } finally {
      setExporting(null)
    }
  }

  const handleExportImage = async () => {
    if (!exportRef.current || exporting) return
    setExporting('image')
    try {
      const topName = rankings[0]?.campaign_name || '评审'
      const date = new Date().toLocaleDateString('zh-CN')
      const filename = `${topName}_对比_${date}`
      await captureElementAsImage(exportRef.current, filename)
    } finally {
      setExporting(null)
    }
  }

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'ranking', label: '综合排名', icon: <Trophy className="h-4 w-4" /> },
    { key: 'persona', label: '评审团详情', icon: <Users className="h-4 w-4" /> },
    { key: 'pairwise', label: '两两对比', icon: <GitCompare className="h-4 w-4" /> },
  ]

  return (
    <div className="space-y-12 pb-20 animate-in fade-in duration-700">

      {/* Header */}
      <section className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl text-primary font-semibold mb-2">深度评审结果</h1>
            {result.summary && (
              <p className="text-muted-foreground max-w-2xl text-balance">
                {result.summary.length > 200 ? result.summary.slice(0, 200) + '...' : result.summary}
              </p>
            )}
            {scoreboard?.too_close_to_call && (
              <span className="inline-flex items-center gap-1.5 mt-3 text-xs font-semibold px-3 py-1.5 rounded-sm bg-amber-100 text-amber-700 border border-amber-200">
                <AlertTriangle className="h-3.5 w-3.5" />
                差距微小，建议慎重
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportPDF}
              disabled={!!exporting}
              className="lab-button lab-button-outline flex items-center gap-2 text-sm"
            >
              {exporting === 'pdf' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              导出 PDF
            </button>
            <button
              onClick={handleExportImage}
              disabled={!!exporting}
              className="lab-button lab-button-outline flex items-center gap-2 text-sm"
            >
              {exporting === 'image' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              导出图片
            </button>
            <button
              onClick={() => { clearEvaluateState(); navigate('/') }}
              className="lab-button lab-button-outline"
            >
              新评审
            </button>
          </div>
        </div>
      </section>

      {/* Export capture area */}
      <div ref={exportRef}>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-border pb-0">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.key
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'ranking' && (
        <RankingTab rankings={rankings} scoreboard={scoreboard} diagnosticsMap={diagnosticsMap} />
      )}
      {activeTab === 'persona' && (
        <PersonaTab panelScores={result.panel_scores} />
      )}
      {activeTab === 'pairwise' && (
        <PairwiseTab
          pairwiseResults={result.pairwise_results}
          rankings={rankings}
          campaignNameMap={campaignNameMap}
        />
      )}

      {/* Footer: Assumptions & Confidence Notes */}
      <section className="space-y-6 border-t border-border pt-8">
        {result.assumptions && result.assumptions.length > 0 && (
          <div>
            <h3 className="text-xs uppercase tracking-wider font-bold text-muted-foreground mb-3">假设前提</h3>
            <ul className="space-y-1.5">
              {result.assumptions.map((a, i) => (
                <li key={i} className="text-sm text-muted-foreground flex gap-2">
                  <span className="text-primary/50 shrink-0">-</span>
                  {a}
                </li>
              ))}
            </ul>
          </div>
        )}
        {result.confidence_notes && result.confidence_notes.length > 0 && (
          <div>
            <h3 className="text-xs uppercase tracking-wider font-bold text-muted-foreground mb-3">置信度说明</h3>
            <ul className="space-y-1.5">
              {result.confidence_notes.map((n, i) => (
                <li key={i} className="text-sm text-muted-foreground flex gap-2">
                  <span className="text-primary/50 shrink-0">-</span>
                  {n}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      </div>{/* end exportRef */}
    </div>
  )
}

/* ========== Tab 1: Overall Ranking ========== */

function RankingTab({ rankings, scoreboard, diagnosticsMap }: { rankings: EvalRanking[]; scoreboard?: EvalScoreboard; diagnosticsMap?: Record<string, VisualDiagnostics> }) {
  return (
    <section className="space-y-8">

      {/* Ranked Cards */}
      <div className="space-y-4">
        {rankings.map(entry => {
          const vs = VERDICT_STYLE[entry.verdict] ?? VERDICT_STYLE.revise
          const sbCampaign = scoreboard?.campaigns.find(c => c.campaign_id === entry.campaign_id)

          return (
            <div key={entry.campaign_id} className="lab-card p-6 space-y-4">
              <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Rank badge */}
                  <div className="flex flex-col items-center justify-center w-10 h-10 rounded-sm bg-primary text-primary-foreground font-display text-xl font-semibold shrink-0">
                    {entry.rank}
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-semibold">{entry.campaign_name}</h3>
                      <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-sm border ${vs.bg} ${vs.text}`}>
                        {vs.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                      <span>胜 {entry.pairwise_wins} / 负 {entry.pairwise_losses}</span>
                      <span>&bull;</span>
                      <span>评审均分 {entry.panel_avg.toFixed(1)}</span>
                    </div>
                  </div>
                </div>

                {/* Composite score */}
                <div className="text-right">
                  <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">综合分</div>
                  <div className="font-mono text-2xl font-medium">{entry.composite_score.toFixed(1)}</div>
                </div>
              </div>

              {/* Strengths & Objections */}
              <div className="flex flex-wrap gap-2">
                {entry.top_strengths.map((s, i) => (
                  <span key={`s-${i}`} className="text-xs font-mono bg-green-50 text-green-700 border border-green-200 px-2 py-1 rounded-sm">
                    {s}
                  </span>
                ))}
                {entry.top_objections.map((o, i) => (
                  <span key={`o-${i}`} className="text-xs font-mono bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-sm">
                    {o}
                  </span>
                ))}
              </div>

              {/* Verdict rationale from scoreboard */}
              {sbCampaign?.verdict_rationale && (
                <p className="text-sm text-muted-foreground leading-relaxed border-t border-border/50 pt-3">
                  {sbCampaign.verdict_rationale}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* BT Score Bar Chart */}
      {scoreboard && <BTBarChart scoreboard={scoreboard} />}

      {/* Radar Chart - Dimension Comparison */}
      {scoreboard && (() => {
        const dimKeys = new Set<string>()
        for (const c of scoreboard.campaigns) {
          for (const k of Object.keys(c.dimension_scores)) dimKeys.add(k)
        }
        if (dimKeys.size === 0) return null

        const radarCampaigns = scoreboard.campaigns.map(c => ({
          name: c.campaign_name,
          dimensions: c.dimension_scores,
        }))

        return (
          <RadarScoreChart
            campaigns={radarCampaigns}
            dimensionLabels={{
              thumb_stop: '停留吸引力',
              clarity: '信息清晰度',
              trust: '信任感',
              conversion_readiness: '转化就绪度',
              claim_risk: '声称风险',
            }}
          />
        )
      })()}

      {/* Visual Diagnostics */}
      {diagnosticsMap && rankings.map(entry => {
        const diag = diagnosticsMap[entry.campaign_id]
        if (!diag) return null
        return (
          <div key={`diag-${entry.campaign_id}`} className="lab-card p-6 space-y-3">
            <h4 className="font-semibold text-sm">{entry.campaign_name}</h4>
            <DiagnosticsPanel diagnostics={diag} />
          </div>
        )
      })}
    </section>
  )
}

function BTBarChart({ scoreboard }: { scoreboard: EvalScoreboard }) {
  const sorted = [...scoreboard.campaigns].sort((a, b) => b.overall_score - a.overall_score)
  const maxScore = sorted.length > 0 ? sorted[0].overall_score : 1

  // Collect unique dimension keys
  const dimensionKeys = new Set<string>()
  for (const c of sorted) {
    for (const k of Object.keys(c.dimension_scores)) {
      dimensionKeys.add(k)
    }
  }
  const dimArray = Array.from(dimensionKeys)

  return (
    <div className="lab-card p-6 space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 className="h-4 w-4 text-primary" />
        <h3 className="font-semibold text-sm uppercase tracking-widest text-primary">BT 综合评分</h3>
      </div>

      {/* Horizontal bar chart */}
      <div className="space-y-3">
        {sorted.map(campaign => (
          <div key={campaign.campaign_id} className="flex items-center gap-3">
            <div className="w-28 text-sm font-medium truncate shrink-0">{campaign.campaign_name}</div>
            <div className="flex-1 h-7 bg-secondary/30 rounded-sm overflow-hidden relative">
              <div
                className="h-full bg-accent rounded-sm transition-all duration-500"
                style={{ width: `${Math.max((campaign.overall_score / maxScore) * 100, 2)}%` }}
              />
            </div>
            <div className="w-12 text-right font-mono text-sm font-medium shrink-0">
              {campaign.overall_score.toFixed(1)}
            </div>
          </div>
        ))}
      </div>

      {/* Dimension scores grid */}
      {dimArray.length > 0 && (
        <div className="border-t border-border pt-4">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">维度分数</div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">方案</th>
                  {dimArray.map(dk => (
                    <th key={dk} className="text-center py-2 px-2 font-semibold text-muted-foreground">
                      {DIMENSION_LABELS[dk] ?? dk}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map(campaign => (
                  <tr key={campaign.campaign_id} className="border-b border-border/30">
                    <td className="py-2 pr-4 font-medium">{campaign.campaign_name}</td>
                    {dimArray.map(dk => (
                      <td key={dk} className="text-center py-2 px-2">
                        {campaign.dimension_scores[dk]?.toFixed(1) ?? '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

/* ========== Tab 2: Persona Details ========== */

function PersonaTab({ panelScores }: { panelScores: EvalPanelScore[] }) {
  // Group by persona_name
  const groups: Record<string, EvalPanelScore[]> = {}
  for (const ps of panelScores) {
    const key = ps.persona_name || ps.persona_id
    if (!groups[key]) groups[key] = []
    groups[key].push(ps)
  }
  const personaNames = Object.keys(groups)

  return (
    <section className="space-y-8">
      {personaNames.map((pName, pIdx) => (
        <div key={pName} className="space-y-4">
          <h3 className="font-display text-xl text-primary border-b border-border pb-3 flex items-center gap-3">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${PERSONA_COLORS[pIdx % PERSONA_COLORS.length]}`}>
              <User className="h-4 w-4" />
            </div>
            {pName}
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {groups[pName].map(score => (
              <PersonaScoreCard key={`${score.persona_id}-${score.campaign_id}`} score={score} colorIdx={pIdx} />
            ))}
          </div>
        </div>
      ))}
    </section>
  )
}

function PersonaScoreCard({ score, colorIdx }: { score: EvalPanelScore; colorIdx: number }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="lab-card p-5 space-y-3">
      <div className="flex items-start gap-3">
        <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${PERSONA_COLORS[colorIdx % PERSONA_COLORS.length]}`}>
          <User className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <span className="font-semibold text-sm">{score.persona_name}</span>
              <span className="text-muted-foreground text-xs ml-2">{score.campaign_id}</span>
            </div>
            <div className="font-mono text-xl font-medium shrink-0">
              {score.score}<span className="text-muted-foreground text-sm">/10</span>
            </div>
          </div>

          {/* Reasoning */}
          {score.reasoning && (
            <div className="mt-2">
              <p className="text-sm text-muted-foreground leading-relaxed">
                {expanded ? score.reasoning : score.reasoning.slice(0, 100)}
                {score.reasoning.length > 100 && !expanded && '...'}
              </p>
              {score.reasoning.length > 100 && (
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="flex items-center gap-1 text-xs text-primary mt-1 hover:underline"
                >
                  {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {expanded ? '收起' : '展开'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Strengths & Objections */}
      <div className="space-y-1.5 pl-12">
        {score.strengths.map((s, i) => (
          <div key={`s-${i}`} className="text-xs text-green-700 flex gap-1.5">
            <span className="shrink-0">+</span>
            {s}
          </div>
        ))}
        {score.objections.map((o, i) => (
          <div key={`o-${i}`} className="text-xs text-red-700 flex gap-1.5">
            <span className="shrink-0">-</span>
            {o}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ========== Tab 3: Pairwise Comparison ========== */

function PairwiseTab({
  pairwiseResults,
  rankings,
  campaignNameMap,
}: {
  pairwiseResults: EvalPairwiseResult[]
  rankings: EvalRanking[]
  campaignNameMap: Record<string, string>
}) {
  const campaignIds = rankings.map(r => r.campaign_id)

  // Build lookup: "a|b" -> result
  const lookup: Record<string, EvalPairwiseResult> = {}
  for (const pr of pairwiseResults) {
    lookup[`${pr.campaign_a_id}|${pr.campaign_b_id}`] = pr
    lookup[`${pr.campaign_b_id}|${pr.campaign_a_id}`] = pr
  }

  function getCell(rowId: string, colId: string) {
    if (rowId === colId) return { label: '-', cls: 'bg-gray-200 text-gray-500' }
    const pr = lookup[`${rowId}|${colId}`]
    if (!pr) return { label: '-', cls: 'bg-gray-100 text-gray-400' }

    const inconsistent = pr.position_swap_consistent === false
    if (pr.winner_id === rowId) {
      return { label: '胜', cls: 'bg-green-100 text-green-700 font-semibold', inconsistent }
    } else if (pr.winner_id === colId) {
      return { label: '负', cls: 'bg-red-100 text-red-700', inconsistent }
    } else {
      return { label: '平', cls: 'bg-gray-100 text-gray-500', inconsistent }
    }
  }

  return (
    <section className="space-y-8">

      {/* Win/Loss Matrix */}
      <div className="lab-card p-6 space-y-4">
        <h3 className="font-semibold text-sm uppercase tracking-widest text-primary mb-4">胜负矩阵</h3>
        <div className="overflow-x-auto">
          <table className="text-xs font-mono w-full">
            <thead>
              <tr>
                <th className="text-left py-2 pr-3 text-muted-foreground font-semibold">方案 \ 对手</th>
                {campaignIds.map(id => (
                  <th key={id} className="text-center py-2 px-2 text-muted-foreground font-semibold min-w-[60px]">
                    {(campaignNameMap[id] ?? id).slice(0, 6)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {campaignIds.map(rowId => (
                <tr key={rowId} className="border-t border-border/30">
                  <td className="py-2 pr-3 font-medium">{campaignNameMap[rowId] ?? rowId}</td>
                  {campaignIds.map(colId => {
                    const cell = getCell(rowId, colId)
                    return (
                      <td key={colId} className={`text-center py-2 px-2 ${cell.cls}`}>
                        <span className="inline-flex items-center gap-0.5">
                          {cell.label}
                          {cell.inconsistent && (
                            <span title="正反序评审结果不一致">
                              <AlertTriangle className="h-3 w-3 text-amber-500 inline-block" />
                            </span>
                          )}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pairwise Detail Cards */}
      <div className="space-y-4">
        {pairwiseResults.map((pr, idx) => {
          const aName = campaignNameMap[pr.campaign_a_id] ?? pr.campaign_a_id
          const bName = campaignNameMap[pr.campaign_b_id] ?? pr.campaign_b_id
          const winnerName = pr.winner_id
            ? (campaignNameMap[pr.winner_id] ?? pr.winner_id)
            : null

          return (
            <div key={idx} className="lab-card p-5 space-y-3">
              <div className="flex items-center gap-3">
                <span className={`font-semibold text-sm ${pr.winner_id === pr.campaign_a_id ? 'text-green-700' : ''}`}>
                  {aName}
                </span>
                <span className="text-muted-foreground text-xs">vs</span>
                <span className={`font-semibold text-sm ${pr.winner_id === pr.campaign_b_id ? 'text-green-700' : ''}`}>
                  {bName}
                </span>
                {winnerName && (
                  <span className="text-xs font-mono bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded-sm ml-auto">
                    {winnerName} 胜出
                  </span>
                )}
                {!winnerName && (
                  <span className="text-xs font-mono bg-gray-100 text-gray-500 px-2 py-0.5 rounded-sm ml-auto">
                    平局
                  </span>
                )}
              </div>

              {/* Dimensions breakdown */}
              {Object.keys(pr.dimensions).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(pr.dimensions).map(([dk, val]) => (
                    <span key={dk} className="text-xs font-mono bg-secondary/30 px-2 py-1 rounded-sm">
                      {DIMENSION_LABELS[dk] ?? dk}: {val}
                    </span>
                  ))}
                </div>
              )}

              {/* Position swap warning */}
              {pr.position_swap_consistent === false && (
                <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-sm px-3 py-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                  <span className="text-xs text-amber-700 font-medium">位置互换后评审结果不一致</span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
