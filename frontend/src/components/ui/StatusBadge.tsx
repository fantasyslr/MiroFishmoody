type StatusTone =
  | 'neutral'
  | 'running'
  | 'done'
  | 'warning'
  | 'draft'
  | 'settlement'

const toneMap: Record<StatusTone, string> = {
  neutral: 'border-mist/30 bg-mist-soft/60 text-ink',
  running: 'border-mist/40 bg-mist-soft text-coffee',
  done: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warning: 'border-wine/20 bg-wine/10 text-wine',
  draft: 'border-line bg-cream text-ink',
  settlement: 'border-amber-200 bg-amber-50 text-amber-700',
}

type StatusBadgeProps = {
  label: string
  tone?: StatusTone
}

export function StatusBadge({ label, tone = 'neutral' }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${toneMap[tone]}`}
    >
      {label}
    </span>
  )
}
