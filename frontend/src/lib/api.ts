const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

// --- Auth Types ---
export type AuthUser = {
  username: string
  display_name: string
  role?: 'admin' | 'user'
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const usesFormData = init?.body instanceof FormData
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: usesFormData
      ? init?.headers
      : {
          'Content-Type': 'application/json',
          ...(init?.headers ?? {}),
        },
    ...init,
  })

  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    const message = data?.error ?? data?.message ?? `Request failed: ${response.status}`
    throw new ApiError(response.status, message)
  }

  return data as T
}

// --- Auth APIs ---
export function login(username: string, password: string) {
  return request<AuthUser>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout() {
  return request<{ status: string }>('/api/auth/logout', {
    method: 'POST',
  })
}

export function getMe() {
  return request<AuthUser>('/api/auth/me')
}

// --- V3 Brandiction Types ---

export type CampaignPlan = {
  id?: string
  name: string
  theme: string
  platform: string
  channel_family: string
  landing_page?: string
  budget: number
  objective?: string
  message_arc?: string
  market?: string
  image_paths?: string[]
}

export type RacePayload = {
  plans: CampaignPlan[]
  sort_by: 'roas_mean' | 'purchase_rate' | 'revenue_mean' | 'cvr_mean'
  include_hypothesis: boolean
  product_line?: string
  audience_segment?: string
  market?: string
  season_tag?: string
}

// Matches BaselineStats.to_dict() from baseline_ranker.py
export type ObservedBaseline = {
  sample_size: number
  roas_mean?: number
  roas_std?: number
  ctr_mean?: number
  cvr_mean?: number
  cpa?: number
  sessions_mean?: number
  purchase_rate?: number
  aov_mean?: number
  revenue_mean?: number
  drift_30d?: Record<string, number>
  drift_60d?: Record<string, number>
  drift_90d?: Record<string, number>
  seasonal_drift?: {
    current_season: string
    sample_in_season: number
    sample_regular: number
    season_vs_regular_roas?: number
    season_vs_regular_cvr?: number
  }
  cold_start_hint?: {
    type: 'cross_category' | 'distribution_estimate'
    note: string
    source_product_lines?: string[]
    discount_applied?: number
    total_interventions_in_db?: number
    roas_range?: { p25: number; p50: number; p75: number }
    cvr_range?: { p25: number; p50: number; p75: number }
    revenue_range?: { p25: number; p50: number; p75: number }
  }
  match_dimensions: string[]
  match_quality: 'exact' | 'partial' | 'fallback' | 'cross_category' | 'cold_start' | 'no_data'
  percentile?: number
}

// Visual adjustment metadata (when image analysis influenced ranking)
export type VisualAdjustment = {
  applied: boolean
  reason: string
  visual_score: number | null
  visual_score_mean?: number
  score_delta?: number
  original_score?: number
}

// Diagnostics types from image analysis
export type VisualDiagnosticIssue = {
  category: 'brand_alignment' | 'visual_quality' | 'messaging' | 'audience_fit' | 'compliance'
  severity: 'high' | 'medium' | 'low'
  description: string
}

export type VisualDiagnosticRecommendation = {
  category: 'brand_alignment' | 'visual_quality' | 'messaging' | 'audience_fit' | 'compliance'
  action: string
  priority: 'high' | 'medium' | 'low'
}

export type VisualDiagnostics = {
  issues: VisualDiagnosticIssue[]
  recommendations: VisualDiagnosticRecommendation[]
}

// Structured visual profile from image analysis
export type VisualProfile = {
  creative_style?: string
  product_visibility?: number
  human_presence?: string
  text_density?: number
  visual_claim_focus?: string
  aesthetic_tone?: string
  trust_signal_strength?: number
  promo_intensity?: number
  premium_vs_mass?: string
  visual_hooks?: string[]
  visual_risks?: string[]
  summary?: string
  consistency_score?: number
  dominant_creative_strategy?: string
  image_count?: number
  diagnostics?: VisualDiagnostics
}

// Single entry in the ranking array from rank_campaigns()
export type RankingEntry = {
  rank: number
  plan: CampaignPlan
  observed_baseline: ObservedBaseline
  score: number
  data_sufficient: boolean
  visual_adjustment?: VisualAdjustment
}

// Hypothesis from predict_impact() — per-plan
export type HypothesisPlan = {
  plan: CampaignPlan
  predicted_delta?: Record<string, number>
  confidence?: number
  reasoning?: string
  similar_interventions?: number
  note?: string
  error?: string
  visual_profile?: VisualProfile
}

// Full /race response shape — matches brandiction.py race_campaigns()
export type RaceResult = {
  observed_baseline: {
    ranking: RankingEntry[]
    sort_by: string
    recommendation: string
  }
  model_hypothesis: {
    note: string
    plans: HypothesisPlan[]
  } | null
  visual_analysis: {
    note: string
    profiles: Record<string, VisualProfile>
  } | null
}

// --- V3 Brandiction APIs ---

export async function raceCampaigns(payload: RacePayload): Promise<RaceResult> {
  return request<RaceResult>('/api/brandiction/race', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export type UploadImageResponse = {
  image_id: string
  url: string
  size: number
}

export async function uploadCampaignImage(file: File, setId: string, campaignId: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('set_id', setId)
  formData.append('campaign_id', campaignId)

  return request<UploadImageResponse>('/api/campaign/upload-image', {
    method: 'POST',
    body: formData,
  })
}

// Temporary store for passing data between pages
const RACE_STATE_KEY = 'mirofishmoody.race_state'
export function saveRaceState(state: { payload: RacePayload, result?: RaceResult }) {
  localStorage.setItem(RACE_STATE_KEY, JSON.stringify(state))
}
export function getRaceState() {
  const raw = localStorage.getItem(RACE_STATE_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) as { payload: RacePayload, result?: RaceResult } } catch { return null }
}
export function clearRaceState() {
  localStorage.removeItem(RACE_STATE_KEY)
}

// --- Evaluate Types ---

export type EvaluatePayload = {
  set_id: string
  campaigns: Array<{
    campaign_id: string
    name: string
    description?: string
    image_paths?: string[]
  }>
  category?: string
  parent_set_id?: string
  brief_type?: 'brand' | 'seeding' | 'conversion'
}

export type TaskStatusResponse = {
  task_id: string
  task_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
  progress_detail: Record<string, unknown>
  result: {
    set_id: string
    campaign_count: number
    top_campaign: string | null
    top_verdict: string | null
    top_overall_score: number | null
    too_close_to_call: boolean
    lead_margin: number
  } | null
  error: string | null
  metadata: Record<string, unknown>
}

export type EvalPanelScore = {
  persona_id: string
  persona_name: string
  campaign_id: string
  score: number
  objections: string[]
  strengths: string[]
  reasoning: string
  dimension_scores: Record<string, unknown>
}

export type EvalPairwiseResult = {
  campaign_a_id: string
  campaign_b_id: string
  winner_id: string | null
  votes: Array<Record<string, unknown>>
  dimensions: Record<string, string>
  position_swap_consistent: boolean
  swap_votes: Array<Record<string, unknown>>
}

export type EvalRanking = {
  campaign_id: string
  campaign_name: string
  rank: number
  composite_score: number
  panel_avg: number
  pairwise_wins: number
  pairwise_losses: number
  verdict: 'ship' | 'revise' | 'kill'
  top_objections: string[]
  top_strengths: string[]
}

export type EvalScoreboardCampaign = {
  campaign_id: string
  campaign_name: string
  overall_score: number
  dimension_scores: Record<string, number>
  rank: number
  verdict: string
  lead_margin_to_next: number | null
  verdict_rationale: string
}

export type EvalScoreboard = {
  campaigns: EvalScoreboardCampaign[]
  lead_margin: number
  too_close_to_call: boolean
  confidence_threshold: number
  rationale_for_uncertainty: string
  dimension_details: Array<{
    dimension_key: string
    dimension_label: string
    campaign_id: string
    score: number
    raw_score: number
  }>
}

export type EvaluateResult = {
  set_id: string
  rankings: EvalRanking[]
  panel_scores: EvalPanelScore[]
  pairwise_results: EvalPairwiseResult[]
  summary: string
  assumptions: string[]
  confidence_notes: string[]
  scoreboard?: EvalScoreboard
  resolution_ready_fields?: Record<string, string>
  campaign_image_map?: Record<string, string[]>
  visual_diagnostics?: Record<string, VisualDiagnostics>  // campaign_id -> diagnostics
}

// --- Evaluate APIs ---

export async function evaluateCampaigns(payload: EvaluatePayload) {
  return request<{ task_id: string; set_id: string; campaign_count: number; message: string }>(
    '/api/campaign/evaluate', { method: 'POST', body: JSON.stringify(payload) }
  )
}

export async function getEvaluateStatus(taskId: string) {
  return request<TaskStatusResponse>(`/api/campaign/evaluate/status/${taskId}`)
}

export async function getEvaluateResult(setId: string) {
  return request<EvaluateResult>(`/api/campaign/result/${setId}`)
}

// --- Evaluate State Helpers ---

const EVALUATE_STATE_KEY = 'mirofishmoody.evaluate_state'
export function saveEvaluateState(state: { taskId: string; setId: string; payload: EvaluatePayload; result?: EvaluateResult }) {
  localStorage.setItem(EVALUATE_STATE_KEY, JSON.stringify(state))
}
export function getEvaluateState() {
  const raw = localStorage.getItem(EVALUATE_STATE_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) as { taskId: string; setId: string; payload: EvaluatePayload; result?: EvaluateResult } } catch { return null }
}
export function clearEvaluateState() {
  localStorage.removeItem(EVALUATE_STATE_KEY)
}

// --- Both Mode State Helpers ---

const BOTH_MODE_KEY = 'mirofishmoody.both_mode'
export function saveBothModeState(state: { evaluateTaskId: string; evaluateSetId: string }) {
  localStorage.setItem(BOTH_MODE_KEY, JSON.stringify(state))
}
export function getBothModeState() {
  const raw = localStorage.getItem(BOTH_MODE_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) as { evaluateTaskId: string; evaluateSetId: string } } catch { return null }
}
export function clearBothModeState() {
  localStorage.removeItem(BOTH_MODE_KEY)
}

// --- Version / Iteration Types ---

export type VersionInfo = {
  set_id: string
  version: number
  created_at: string
  campaign_names: string[]
  overall_scores: Record<string, number>
}

export type VersionCompareResult = {
  v1: { set_id: string; version: number; scoreboard: EvalScoreboard }
  v2: { set_id: string; version: number; scoreboard: EvalScoreboard }
  deltas: Record<string, {
    overall_delta: number
    dimension_deltas: Record<string, number>
  }>
}

// --- Version / Iteration APIs ---

export function getVersionHistory(setId: string) {
  return request<{ versions: VersionInfo[] }>(`/api/campaign/version-history/${setId}`)
}

export function getVersionCompare(v1SetId: string, v2SetId: string) {
  return request<VersionCompareResult>(`/api/campaign/compare?v1=${v1SetId}&v2=${v2SetId}`)
}

// --- Iterate State Helpers ---

const ITERATE_STATE_KEY = 'mirofishmoody.iterate_state'
export function saveIterateState(state: { parentSetId: string; parentCampaignNames: string[] }) {
  localStorage.setItem(ITERATE_STATE_KEY, JSON.stringify(state))
}
export function getIterateState() {
  const raw = localStorage.getItem(ITERATE_STATE_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) as { parentSetId: string; parentCampaignNames: string[] } } catch { return null }
}
export function clearIterateState() {
  localStorage.removeItem(ITERATE_STATE_KEY)
}

// --- Trends Types ---

export type TrendDataPoint = {
  set_id: string
  timestamp: string
  campaigns: Record<string, number>
}

export type TrendsResponse = {
  data_points: TrendDataPoint[]
  campaign_names: string[]
  category_filter: string
}

// --- Trends APIs ---

export function getTrends(category: string = 'all') {
  return request<TrendsResponse>(`/api/campaign/trends?category=${category}`)
}

// --- Admin APIs ---
export function getBrandictionStats() {
  return request<Record<string, unknown>>('/api/brandiction/stats')
}

export function getRaceHistory() {
  return request<{ runs: Array<{
    id: string
    date: string
    plans_count: number
    top_recommendation: string
    status: string
    hit: boolean | null
  }> }>('/api/brandiction/race-history')
}
