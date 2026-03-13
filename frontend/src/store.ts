import { create } from 'zustand'

export interface Plan {
  id: string
  name: string
  productLine: 'moodyplus' | 'colored_lenses'
  description: string
  imageFiles: File[]
  imagePreviews: string[]
}

interface ReviewStore {
  notes: string
  plans: Plan[]
  setNotes: (notes: string) => void
  addPlan: () => void
  removePlan: (id: string) => void
  updatePlan: (id: string, updates: Partial<Plan>) => void
  addImages: (planId: string, files: File[]) => void
  removeImage: (planId: string, index: number) => void
  reset: () => void
}

function makePlan(): Plan {
  return {
    id: crypto.randomUUID(),
    name: '',
    productLine: 'moodyplus',
    description: '',
    imageFiles: [],
    imagePreviews: [],
  }
}

function initialPlans(): Plan[] {
  return [makePlan(), makePlan()]
}

export const useReviewStore = create<ReviewStore>((set) => ({
  notes: '',
  plans: initialPlans(),
  setNotes: (notes) => set({ notes }),
  addPlan: () =>
    set((state) => {
      if (state.plans.length >= 4) return state
      return { plans: [...state.plans, makePlan()] }
    }),
  removePlan: (id) =>
    set((state) => {
      if (state.plans.length <= 2) return state
      const plan = state.plans.find((p) => p.id === id)
      if (plan) {
        plan.imagePreviews.forEach((url) => URL.revokeObjectURL(url))
      }
      return { plans: state.plans.filter((p) => p.id !== id) }
    }),
  updatePlan: (id, updates) =>
    set((state) => ({
      plans: state.plans.map((p) => (p.id === id ? { ...p, ...updates } : p)),
    })),
  addImages: (planId, files) =>
    set((state) => ({
      plans: state.plans.map((p) => {
        if (p.id !== planId) return p
        const allowed = files.slice(0, 5 - p.imageFiles.length)
        return {
          ...p,
          imageFiles: [...p.imageFiles, ...allowed],
          imagePreviews: [...p.imagePreviews, ...allowed.map((f) => URL.createObjectURL(f))],
        }
      }),
    })),
  removeImage: (planId, index) =>
    set((state) => ({
      plans: state.plans.map((p) => {
        if (p.id !== planId) return p
        URL.revokeObjectURL(p.imagePreviews[index])
        return {
          ...p,
          imageFiles: p.imageFiles.filter((_, i) => i !== index),
          imagePreviews: p.imagePreviews.filter((_, i) => i !== index),
        }
      }),
    })),
  reset: () =>
    set((state) => {
      state.plans.forEach((p) => p.imagePreviews.forEach((url) => URL.revokeObjectURL(url)))
      return { notes: '', plans: initialPlans() }
    }),
}))
