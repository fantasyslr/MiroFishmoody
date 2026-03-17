type PercentileBarProps = {
  percentile: number
  label?: string
}

export function PercentileBar({ percentile, label }: PercentileBarProps) {
  const clamped = Math.max(0, Math.min(100, percentile))

  return (
    <div className="space-y-1">
      {label && (
        <p className="text-sm font-medium text-gray-700">{label}</p>
      )}
      <div className="relative h-3 w-full rounded-full bg-gray-200">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-accent transition-all duration-500"
          style={{ width: `${clamped}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 h-4 w-4 rounded-full bg-accent ring-2 ring-white shadow"
          style={{ left: `calc(${clamped}% - 8px)` }}
        />
      </div>
      <p className="text-xs text-gray-500">
        超过 {Math.round(clamped)}% 的历史 campaign
      </p>
    </div>
  )
}
