import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getEvaluateState, getEvaluateStatus, getEvaluateResult, saveEvaluateState } from '../lib/api'
import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react'
import { StepIndicator } from '../components/StepIndicator'
import { LogBuffer } from '../components/LogBuffer'

const EVAL_STAGES = [
  { key: 'panel', label: 'Audience Panel 评审', range: [0, 40] as const },
  { key: 'pairwise', label: 'Pairwise 对决', range: [40, 80] as const },
  { key: 'scoring', label: '综合评分', range: [80, 90] as const },
  { key: 'summary', label: '总结报告', range: [90, 100] as const },
]

function getCurrentStageIndex(progress: number): number {
  for (let i = EVAL_STAGES.length - 1; i >= 0; i--) {
    if (progress >= EVAL_STAGES[i].range[0]) return i
  }
  return 0
}

const STEP_LABELS = ['方案解析', '评审分析', '结果汇总']
// progress 0-39 = step 0, 40-79 = step 1, 80-100 = step 2
function progressToStep(p: number): number {
  if (p < 40) return 0
  if (p < 80) return 1
  return 2
}

export function EvaluatePage() {
  const navigate = useNavigate()
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [, setStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending')
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const startedRef = useRef(false)

  useEffect(() => {
    const state = getEvaluateState()
    if (!state?.taskId) {
      navigate('/')
      return
    }

    // Guard against StrictMode double-fire
    if (startedRef.current) return
    startedRef.current = true

    const taskId = state.taskId
    const setId = state.setId

    const interval = setInterval(async () => {
      try {
        const res = await getEvaluateStatus(taskId)
        setProgress(res.progress)
        setMessage(res.message)
        setStatus(res.status)
        if (res.message) {
          setLogs(prev => [...prev, res.message])
        }

        if (res.status === 'completed') {
          clearInterval(interval)
          try {
            const result = await getEvaluateResult(setId)
            saveEvaluateState({ ...state, result })
            navigate('/evaluate-result')
          } catch (err) {
            setError(err instanceof Error ? err.message : '获取评审结果失败')
          }
        } else if (res.status === 'failed') {
          clearInterval(interval)
          setError(res.error || '评审任务失败')
        }
      } catch (err) {
        clearInterval(interval)
        setError(err instanceof Error ? err.message : '轮询状态失败，请检查网络连接')
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [navigate])

  if (error) {
    return (
      <div className="min-h-screen bg-primary text-primary-foreground flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-lg space-y-8 text-center">
          <AlertCircle className="h-12 w-12 text-accent mx-auto" />
          <h2 className="font-display text-2xl font-semibold">评审失败</h2>
          <p className="text-primary-foreground/60 text-sm font-mono">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="lab-button lab-button-outline border-primary-foreground/20 text-primary-foreground hover:bg-primary-foreground/10"
          >
            返回首页
          </button>
        </div>
      </div>
    )
  }

  const currentStageIndex = getCurrentStageIndex(progress)
  const state = getEvaluateState()
  const campaignCount = state?.payload?.campaigns?.length ?? 0

  return (
    <div className="min-h-screen bg-primary text-primary-foreground flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-12">
        <div className="space-y-4 text-center">
          <h2 className="font-display text-4xl font-semibold">深度评审进行中</h2>
          <p className="text-primary-foreground/60 text-sm font-mono uppercase tracking-wider">
            正在评审 {campaignCount} 个方案
          </p>
        </div>

        <StepIndicator steps={STEP_LABELS} currentStep={progressToStep(progress)} />

        <div className="space-y-4">
          {EVAL_STAGES.map((stage, i) => {
            const isCompleted = i < currentStageIndex
            const isActive = i === currentStageIndex

            return (
              <div
                key={stage.key}
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
                  {stage.label}
                </span>
              </div>
            )
          })}
        </div>

        {/* Progress bar */}
        <div className="space-y-2">
          <div className="w-full h-2 bg-primary-foreground/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-center text-sm font-mono text-primary-foreground/60">
            {progress}%
          </p>
        </div>

        {message && (
          <p className="text-center text-xs text-primary-foreground/40 font-mono">
            {message}
          </p>
        )}

        {logs.length > 0 && (
          <div className="mt-4 h-24">
            <LogBuffer messages={logs} className="h-24" />
          </div>
        )}

        <div className="pt-8 border-t border-primary-foreground/10 text-center">
          <p className="text-xs text-primary-foreground/40 uppercase tracking-widest">
            请勿关闭此窗口
          </p>
        </div>
      </div>
    </div>
  )
}
