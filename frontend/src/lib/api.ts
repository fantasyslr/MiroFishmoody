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
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
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
}

// Single entry in the ranking array from rank_campaigns()
export type RankingEntry = {
  rank: number
  plan: CampaignPlan
  observed_baseline: ObservedBaseline
  score: number
  data_sufficient: boolean
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
}

// --- V3 Brandiction APIs ---

export async function raceCampaigns(payload: RacePayload): Promise<RaceResult> {
  return request<RaceResult>('/api/brandiction/race', {
    method: 'POST',
    body: JSON.stringify(payload),
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
