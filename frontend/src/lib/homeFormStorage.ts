// frontend/src/lib/homeFormStorage.ts
// sessionStorage persistence for HomePage form state

import type { CampaignPlan, RacePayload } from './api'

export const HOME_FORM_KEY = 'miro_home_form_v1'

export type HomeFormSnapshot = {
  mode: 'race' | 'evaluate' | 'both'
  market: string
  productLine: string
  sortBy: RacePayload['sort_by']
  seasonTag: string
  plans: CampaignPlan[]
  briefType?: 'brand' | 'seeding' | 'conversion' | ''
}

export function saveHomeForm(snapshot: HomeFormSnapshot): void {
  try {
    sessionStorage.setItem(HOME_FORM_KEY, JSON.stringify(snapshot))
  } catch {
    // sessionStorage quota exceeded or unavailable — silently ignore
  }
}

export function loadHomeForm(): HomeFormSnapshot | null {
  try {
    const raw = sessionStorage.getItem(HOME_FORM_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as HomeFormSnapshot
    // Basic validation — if plans array missing or empty, return null
    if (!parsed.plans || parsed.plans.length === 0) return null
    return parsed
  } catch {
    return null
  }
}

export function clearHomeForm(): void {
  try {
    sessionStorage.removeItem(HOME_FORM_KEY)
  } catch {
    // ignore
  }
}
