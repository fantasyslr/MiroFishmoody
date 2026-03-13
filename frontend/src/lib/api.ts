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
  submitted_by?: string
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
    top_overall_score?: number | null
    too_close_to_call?: boolean
    lead_margin?: number
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

export type ScoreBoardCampaign = {
  campaign_id: string
  campaign_name: string
  overall_score: number
  dimension_scores?: Record<string, number>
  rank: number
  verdict: 'ship' | 'revise' | 'kill'
  lead_margin_to_next: number | null
  verdict_rationale: string
}

export type DimensionDetail = {
  dimension_key: string
  dimension_label: string
  campaign_id: string
  score: number
  raw_score: number
}

export type CampaignImageMap = {
  /** All images for this set (key "_all"), or per-campaign keyed by campaign_id */
  _all?: string[]
  [campaignId: string]: string[] | undefined
}

export type EvaluationResult = {
  set_id: string
  rankings: Ranking[]
  summary: string
  assumptions: string[]
  confidence_notes: string[]
  scoreboard?: {
    campaigns: ScoreBoardCampaign[]
    lead_margin: number
    too_close_to_call: boolean
    confidence_threshold: number
    rationale_for_uncertainty: string
    dimension_details?: DimensionDetail[]
  }
  resolution_ready_fields?: Record<string, string>
  campaign_image_map?: CampaignImageMap
}

export type ParseBriefPayload = {
  brief_text: string
  product_line: 'moodyplus' | 'colored_lenses'
}

export type ParseBriefResponse = {
  parsed: {
    name: string
    product_line: string
    target_audience: string
    core_message: string
    channels: string[]
    creative_direction: string
    budget_range: string
    promo_mechanic: string
    kv_description: string
  }
  confidence: 'high' | 'medium' | 'low'
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

export function parseBrief(payload: ParseBriefPayload) {
  return request<ParseBriefResponse>('/api/campaign/parse-brief', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function triggerRecalibrate() {
  return request<Record<string, unknown>>('/api/campaign/recalibrate', {
    method: 'POST',
  })
}

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
  metadata?: {
    set_id?: string
    submitted_by?: string
    campaign_names?: string[]
    campaign_count?: number
    submitted_at?: string
  }
}

export function getTasks() {
  return request<{ tasks: TaskListItem[] }>('/api/campaign/tasks')
}

export type ImageUploadResponse = {
  image_id: string
  path: string
  size: number
}

export async function uploadImage(file: File, setId?: string, campaignId?: string): Promise<ImageUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (setId) formData.append('set_id', setId)
  if (campaignId) formData.append('campaign_id', campaignId)

  const response = await fetch(`${API_BASE}/api/campaign/upload-image`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  })

  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    const message = data?.error ?? `Upload failed: ${response.status}`
    throw new ApiError(response.status, message)
  }

  return data as ImageUploadResponse
}

export type CampaignImageListItem = {
  filename: string
  url: string
}

export function getCampaignImages(setId: string) {
  return request<{ images: CampaignImageListItem[] }>(`/api/campaign/images/${setId}`)
}

/**
 * Build the full URL for a campaign image path returned by the API.
 * Handles both absolute URLs and relative paths like "/api/campaign/image-file/...".
 */
export function campaignImageUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_BASE}${path}`
}

export async function exportResult(setId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/campaign/export/${setId}`, {
    credentials: 'include',
  })

  if (!response.ok) {
    const text = await response.text()
    const data = text ? JSON.parse(text) : null
    const message = data?.error ?? `Export failed: ${response.status}`
    throw new ApiError(response.status, message)
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `evaluation_${setId}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
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
