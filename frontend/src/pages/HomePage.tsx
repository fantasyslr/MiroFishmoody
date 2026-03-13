import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, X, UploadCloud, ArrowRight } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { cn, uuid } from '../utils'
import { useReviewStore } from '../store'
import {
  evaluateCampaigns,
  getLatestReviewSession,
  saveLatestReviewSession,
  uploadImage,
} from '../lib/api'

export function HomePage() {
  const navigate = useNavigate()
  const { notes, setNotes, plans, addPlan, removePlan, updatePlan, addImages, removeImage } =
    useReviewStore()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const latest = getLatestReviewSession()
  const canStart = plans.length >= 2 && plans.every((p) => p.name.trim() !== '')

  const handleImageUpload = (planId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return
    const valid = Array.from(files).filter((f) =>
      ['image/jpeg', 'image/png', 'image/webp'].includes(f.type),
    )
    addImages(planId, valid)
    e.target.value = ''
  }

  const handleStart = async () => {
    if (!canStart || isSubmitting) return
    setIsSubmitting(true)
    setSubmitError('')

    try {
      const setId = uuid()

      // Upload images per campaign
      for (const plan of plans) {
        for (const file of plan.imageFiles) {
          try {
            await uploadImage(file, setId, plan.id)
          } catch {
            // non-fatal
          }
        }
      }

      const response = await evaluateCampaigns({
        set_id: setId,
        context: notes.trim(),
        campaigns: plans.map((p) => ({
          id: p.id,
          name: p.name.trim(),
          product_line: p.productLine,
          target_audience: '',
          core_message: p.description.trim(),
          channels: [],
          creative_direction: '',
        })),
      })

      saveLatestReviewSession({
        taskId: response.task_id,
        setId: response.set_id,
        reviewName: plans.map((p) => p.name.trim()).join(' vs '),
      })

      navigate(`/running?taskId=${response.task_id}&setId=${response.set_id}`)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : '提交失败，请稍后再试')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="pb-24">
      {latest?.taskId && (
        <div
          onClick={() =>
            navigate(`/running?taskId=${latest.taskId}&setId=${latest.setId}`)
          }
          className="mb-8 flex cursor-pointer items-center justify-between rounded-xl border border-stone-200 bg-stone-100 p-4 transition-colors hover:bg-stone-200/50"
        >
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
            <span className="text-sm font-medium">
              你有一个评审正在运行{latest.reviewName ? `：${latest.reviewName}` : ''}
            </span>
          </div>
          <ArrowRight className="h-4 w-4 text-stone-400" />
        </div>
      )}

      <div className="mb-10">
        <h1 className="mb-2 text-2xl font-semibold tracking-tight">新建评审</h1>
        <p className="text-sm text-stone-500">输入 2-4 个营销方案，AI 将自动进行两两对决评审。</p>
      </div>

      <div className="mb-8">
        <label className="mb-2 block text-sm font-medium text-stone-700">评审备注（可选）</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="简述本轮评审的背景、目标或特殊要求..."
          className="h-20 w-full resize-none rounded-xl border border-stone-200 bg-white px-4 py-3 outline-none transition-all placeholder:text-stone-400 focus:border-stone-400 focus:ring-1 focus:ring-stone-400"
        />
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">方案列表</h2>
          {plans.length < 4 && (
            <button
              onClick={addPlan}
              className="flex items-center gap-1.5 rounded-lg bg-stone-100 px-3 py-1.5 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-200 hover:text-stone-900"
            >
              <Plus className="h-4 w-4" />
              添加方案
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <AnimatePresence mode="popLayout">
            {plans.map((plan, index) => (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                key={plan.id}
                className="group relative rounded-2xl border border-stone-200 bg-white p-6 shadow-sm"
              >
                {plans.length > 2 && (
                  <button
                    onClick={() => removePlan(plan.id)}
                    className="absolute right-4 top-4 rounded-lg p-1.5 text-stone-400 opacity-0 transition-all hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}

                <div className="mb-6">
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-stone-400">
                    方案 {String.fromCharCode(65 + index)}
                  </div>
                  <input
                    type="text"
                    value={plan.name}
                    onChange={(e) => updatePlan(plan.id, { name: e.target.value })}
                    placeholder="输入方案名称..."
                    className="w-full border-none bg-transparent p-0 text-2xl font-semibold outline-none placeholder:text-stone-300 focus:ring-0"
                  />
                </div>

                <div className="mb-6">
                  <label className="mb-2 block text-xs font-medium text-stone-500">品类</label>
                  <div className="inline-flex rounded-lg border border-stone-200 bg-stone-50 p-0.5">
                    <button
                      type="button"
                      onClick={() => updatePlan(plan.id, { productLine: 'moodyplus' })}
                      className={cn(
                        'rounded-md px-4 py-1.5 text-sm font-medium',
                        plan.productLine === 'moodyplus'
                          ? 'bg-stone-900 text-white shadow-sm'
                          : 'text-stone-500 hover:text-stone-700',
                      )}
                    >
                      透明片
                    </button>
                    <button
                      type="button"
                      onClick={() => updatePlan(plan.id, { productLine: 'colored_lenses' })}
                      className={cn(
                        'rounded-md px-4 py-1.5 text-sm font-medium',
                        plan.productLine === 'colored_lenses'
                          ? 'bg-stone-900 text-white shadow-sm'
                          : 'text-stone-500 hover:text-stone-700',
                      )}
                    >
                      彩片
                    </button>
                  </div>
                </div>

                <div className="mb-6">
                  <label className="mb-2 block text-xs font-medium text-stone-500">方案描述</label>
                  <textarea
                    value={plan.description}
                    onChange={(e) => updatePlan(plan.id, { description: e.target.value })}
                    placeholder="目标人群、卖点、渠道、促销等..."
                    className="h-32 w-full resize-none rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm outline-none transition-all placeholder:text-stone-400 focus:border-stone-400 focus:bg-white"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-xs font-medium text-stone-500">
                    参考图片 ({plan.imageFiles.length}/5)
                  </label>
                  {plan.imagePreviews.length > 0 && (
                    <div className="mb-3 grid grid-cols-5 gap-2">
                      {plan.imagePreviews.map((url, i) => (
                        <div
                          key={i}
                          className="group/img relative aspect-square overflow-hidden rounded-lg border border-stone-200 bg-stone-50"
                        >
                          <img src={url} alt="" className="h-full w-full object-cover" />
                          <button
                            onClick={() => removeImage(plan.id, i)}
                            className="absolute right-1 top-1 rounded-md bg-black/50 p-1 text-white opacity-0 transition-opacity hover:bg-black/70 group-hover/img:opacity-100"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  {plan.imageFiles.length < 5 && (
                    <label className="flex h-24 w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-stone-200 transition-all hover:border-stone-400 hover:bg-stone-50">
                      <UploadCloud className="mb-2 h-6 w-6 text-stone-400" />
                      <p className="text-xs text-stone-400">点击上传图片</p>
                      <input
                        type="file"
                        className="hidden"
                        multiple
                        accept="image/jpeg,image/png,image/webp"
                        onChange={(e) => handleImageUpload(plan.id, e)}
                      />
                    </label>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {submitError && (
        <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
          {submitError}
        </div>
      )}

      <div className="pointer-events-none fixed bottom-0 left-0 right-0 z-20 flex justify-center bg-gradient-to-t from-[#FDFCFB] via-[#FDFCFB] to-transparent p-6">
        <button
          onClick={handleStart}
          disabled={!canStart || isSubmitting}
          className="pointer-events-auto flex w-full max-w-md items-center justify-center gap-2 rounded-2xl bg-stone-900 py-4 text-lg font-medium text-white shadow-xl shadow-stone-900/10 transition-all hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-30"
        >
          {isSubmitting ? '正在提交...' : '开始评审'}
          {!isSubmitting && <ArrowRight className="h-5 w-5" />}
        </button>
      </div>
    </motion.div>
  )
}
