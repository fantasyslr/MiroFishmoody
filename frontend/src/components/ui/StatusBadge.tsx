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
  done: 'border-coffee/20 bg-coffee/10 text-coffee',
  warning: 'border-wine/20 bg-wine/10 text-wine',
  draft: 'border-line bg-cream text-ink',
  settlement: 'border-wine/15 bg-wine/8 text-ink',
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
