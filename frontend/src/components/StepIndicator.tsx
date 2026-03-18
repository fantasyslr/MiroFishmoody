type StepIndicatorProps = {
  steps: string[]
  currentStep: number // 0-based index of active step
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center w-full">
      {steps.map((label, i) => {
        const isDone = i < currentStep
        const isActive = i === currentStep
        return (
          <div key={i} className="flex items-center flex-1 last:flex-none">
            {/* Step circle */}
            <div className="flex flex-col items-center gap-1.5 shrink-0">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-mono font-semibold transition-all duration-500 ${
                  isDone
                    ? 'bg-accent text-accent-foreground'
                    : isActive
                      ? 'bg-primary text-primary-foreground ring-4 ring-primary/20'
                      : 'bg-primary/20 text-primary-foreground/40'
                }`}
              >
                {isDone ? '✓' : i + 1}
              </div>
              <span
                className={`text-[11px] font-mono whitespace-nowrap transition-all duration-300 ${
                  isActive
                    ? 'text-primary-foreground font-semibold'
                    : isDone
                      ? 'text-primary-foreground/50'
                      : 'text-primary-foreground/25'
                }`}
              >
                {label}
              </span>
            </div>
            {/* Connector line between steps */}
            {i < steps.length - 1 && (
              <div className="flex-1 h-px mx-2 mt-[-20px] relative overflow-hidden bg-primary/20">
                <div
                  className="h-full bg-accent transition-all duration-700"
                  style={{ width: isDone ? '100%' : '0%' }}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
