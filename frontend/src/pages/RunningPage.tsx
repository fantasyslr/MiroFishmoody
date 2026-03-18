import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRaceState, raceCampaigns, saveRaceState } from '../lib/api'
import { Loader2, AlertCircle } from 'lucide-react'
import { StepIndicator } from '../components/StepIndicator'
import { SplitPanel } from '../components/SplitPanel'
import { LogBuffer } from '../components/LogBuffer'

const RACE_STEPS = ['提交任务', '推演计算', '生成结果']
// Race is synchronous: once we hit this view we're at step 1 (index 1 = 推演计算)
const RACE_CURRENT_STEP = 1

export function RunningPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
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

    setLogs(['正在提交推演任务...'])

    raceCampaigns(state.payload)
      .then(result => {
        saveRaceState({ ...state, result })
        navigate('/result')
      })
      .catch(err => {
        setError(err.message || '推演失败，请检查后端连接')
      })
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
      <div className="w-full max-w-2xl space-y-10">
        <div className="space-y-2 text-center">
          <h2 className="font-display text-4xl font-semibold">推演进行中</h2>
          <p className="text-primary-foreground/60 text-sm font-mono uppercase tracking-wider">
            正在处理 {getRaceState()?.payload?.plans?.length || 0} 个策略方向
          </p>
        </div>

        <StepIndicator steps={RACE_STEPS} currentStep={RACE_CURRENT_STEP} />

        <SplitPanel
          left={
            <div className="space-y-4">
              <div className="text-xs font-mono text-primary-foreground/40 uppercase tracking-wider">进度</div>
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-primary-foreground/80" />
                <p className="text-primary-foreground/50 text-xs font-mono text-center">
                  推演通常需要 10-20 秒
                </p>
              </div>
            </div>
          }
          right={
            <div className="space-y-2 h-32">
              <div className="text-xs font-mono text-primary-foreground/40 uppercase tracking-wider">日志</div>
              <LogBuffer messages={logs} className="h-24" />
            </div>
          }
        />

        <div className="text-center">
          <p className="text-xs text-primary-foreground/30 uppercase tracking-widest">请勿关闭此窗口</p>
        </div>
      </div>
    </div>
  )
}
