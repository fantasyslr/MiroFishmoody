import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRaceState, raceCampaigns, saveRaceState } from '../lib/api'
import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react'

const STEPS = [
  'Initializing BrandState Engine v3...',
  'Compiling observed historical baselines...',
  'Extracting empirical funnel proxies (sessions, PDP, ATC, ROAS)...',
  'Running perception model hypothesis...',
  'Synthesizing recommendation...',
  'Finalizing race resolution...'
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
          <h2 className="font-display text-2xl font-semibold">Evaluation Failed</h2>
          <p className="text-primary-foreground/60 text-sm font-mono">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="lab-button lab-button-outline border-primary-foreground/20 text-primary-foreground hover:bg-primary-foreground/10"
          >
            Return to Builder
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-primary text-primary-foreground flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-12">
        <div className="space-y-4 text-center">
          <h2 className="font-display text-4xl font-semibold">Evaluation in Progress</h2>
          <p className="text-primary-foreground/60 text-sm font-mono uppercase tracking-wider">
            Processing {getRaceState()?.payload?.plans?.length || 0} strategic directions
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
            Do not close this window
          </p>
        </div>
      </div>
    </div>
  )
}
