import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRaceState, raceCampaigns, saveRaceState } from '../lib/api'
import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react'

const STEPS = [
  '正在初始化 BrandState 引擎 v3...',
  '正在编译历史基线数据...',
  '正在提取经验漏斗指标（sessions, PDP, ATC, ROAS）...',
  '正在运行认知模型假设...',
  '正在综合生成建议...',
  '正在完成评估结算...'
]

export function RunningPage() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const startedRef = useRef(false)

  useEffect(() => {
    const state = getRaceState()
    if (!state?.payload) {
      navigate('/')
      return
    }

    // Guard against StrictMode double-fire
    if (startedRef.current) return
    startedRef.current = true

    // Visual step progression
    const interval = setInterval(() => {
      setCurrentStep(s => (s < STEPS.length - 1 ? s + 1 : s))
    }, 2500)

    // Actual API call — no mock fallback, errors surface honestly
    raceCampaigns(state.payload).then(result => {
      saveRaceState({ ...state, result })
      clearInterval(interval)
      navigate('/result')
    }).catch(err => {
      clearInterval(interval)
      setError(err.message || 'Race evaluation failed. Check backend connection.')
    })

    return () => clearInterval(interval)
  }, [navigate])

  if (error) {
    return (
      <div className="min-h-screen bg-primary text-primary-foreground flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-lg space-y-8 text-center">
          <AlertCircle className="h-12 w-12 text-accent mx-auto" />
          <h2 className="font-display text-2xl font-semibold">评估失败</h2>
          <p className="text-primary-foreground/60 text-sm font-mono">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="lab-button lab-button-outline border-primary-foreground/20 text-primary-foreground hover:bg-primary-foreground/10"
          >
            返回构建器
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-primary text-primary-foreground flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-12">
        <div className="space-y-4 text-center">
          <h2 className="font-display text-4xl font-semibold">评估进行中</h2>
          <p className="text-primary-foreground/60 text-sm font-mono uppercase tracking-wider">
            正在处理 {getRaceState()?.payload?.plans?.length || 0} 个策略方向
          </p>
        </div>

        <div className="space-y-4">
          {STEPS.map((step, i) => {
            const isCompleted = i < currentStep
            const isActive = i === currentStep

            return (
              <div
                key={i}
                className={`flex items-center gap-4 transition-all duration-500 ${
                  isActive ? 'opacity-100 translate-x-2' :
                  isCompleted ? 'opacity-50' : 'opacity-20'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-5 w-5 text-accent" />
                ) : isActive ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary-foreground" />
                ) : (
                  <Circle className="h-5 w-5" />
                )}
                <span className={`font-mono text-sm ${isActive ? 'text-primary-foreground' : ''}`}>
                  {step}
                </span>
              </div>
            )
          })}
        </div>

        <div className="pt-8 border-t border-primary-foreground/10 text-center">
          <p className="text-xs text-primary-foreground/40 uppercase tracking-widest">
            请勿关闭此窗口
          </p>
        </div>
      </div>
    </div>
  )
}
