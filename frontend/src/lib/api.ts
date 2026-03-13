const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const LATEST_REVIEW_KEY = 'mirofishmoody.latest-review'

export type CampaignInput = {
  id: string
  name: string
  product_line: 'moodyplus' | 'colored_lenses'
  target_audience: string
  core_message: string
  channels: string[]
  creative_direction: string
  budget_range?: string
  kv_description?: string
  promo_mechanic?: string
}

export type EvaluatePayload = {
  set_id?: string
  context: string
  campaigns: CampaignInput[]
}

export type EvaluateResponse = {
  task_id: string
  set_id: string
  campaign_count: number
  message: string
}

export type TaskStatusResponse = {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
  error?: string | null
  result?: {
    set_id: string
    campaign_count: number
    top_campaign?: string | null
    top_verdict?: string | null
    top_win_probability?: number | null
    no_clear_edge?: boolean
    spread?: number
  } | null
}

export type Ranking = {
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

export type ProbabilityBoardCampaign = {
  campaign_id: string
  campaign_name: string
  win_probability: number
  sub_markets?: Record<string, number>
  rank: number
  verdict: 'ship' | 'revise' | 'kill'
  spread_to_next: number | null
  verdict_rationale: string
}

export type EvaluationResult = {
  set_id: string
  rankings: Ranking[]
  summary: string
  assumptions: string[]
  confidence_notes: string[]
  probability_board?: {
    campaigns: ProbabilityBoardCampaign[]
    spread: number
    no_clear_edge: boolean
    no_trade_band: number
    rationale_for_uncertainty: string
  }
  resolution_ready_fields?: Record<string, string>
}

export type ResolvePayload = {
  set_id: string
  winner_campaign_id: string
  actual_metrics: Record<string, number>
  notes?: string
}

export type ResolveResponse = {
  status: 'resolved'
  set_id: string
  winner: string
  predicted_win_prob: number
  recalibrate: string
}

export type CalibrationResponse = {
  resolution_count: number
  resolved_set_count: number
  sets_with_predictions: number
  calibration_supported: boolean
  calibration_ready: boolean
  last_calibrated_at?: string | null
  judge_stats_count: number
  persona_calibration: string
  judge_calibration: string
  message: string
}

export type LatestReviewSession = {
  setId: string
  taskId?: string
  reviewName?: string
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

export function evaluateCampaigns(payload: EvaluatePayload) {
  return request<EvaluateResponse>('/api/campaign/evaluate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getTaskStatus(taskId: string) {
  return request<TaskStatusResponse>(`/api/campaign/evaluate/status/${taskId}`)
}

export function getResult(setId: string) {
  return request<EvaluationResult>(`/api/campaign/result/${setId}`)
}

export function resolveEvaluation(payload: ResolvePayload) {
  return request<ResolveResponse>('/api/campaign/resolve', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getCalibration() {
  return request<CalibrationResponse>('/api/campaign/calibration')
}

export function triggerRecalibrate() {
  return request<Record<string, unknown>>('/api/campaign/recalibrate', {
    method: 'POST',
  })
}

export type TaskListItem = {
  task_id: string
  task_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  progress: number
  message: string
  result?: Record<string, unknown> | null
  error?: string | null
}

export function getTasks() {
  return request<{ tasks: TaskListItem[] }>('/api/campaign/tasks')
}

export function saveLatestReviewSession(session: LatestReviewSession) {
  localStorage.setItem(LATEST_REVIEW_KEY, JSON.stringify(session))
}

export function getLatestReviewSession(): LatestReviewSession | null {
  const raw = localStorage.getItem(LATEST_REVIEW_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as LatestReviewSession
  } catch {
    localStorage.removeItem(LATEST_REVIEW_KEY)
    return null
  }
}
