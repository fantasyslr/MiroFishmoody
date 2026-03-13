type StateOverlayProps = {
  status: 'idle' | 'loading' | 'error' | 'empty'
  message?: string
  onRetry?: () => void
}

export function StateOverlay({ status, message, onRetry }: StateOverlayProps) {
  if (status === 'idle') return null

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      {status === 'loading' ? (
        <>
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-coffee" />
          <p className="text-sm text-ink/70">{message ?? '正在加载...'}</p>
        </>
      ) : status === 'error' ? (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-wine/20 bg-wine/10">
            <span className="text-lg text-wine">!</span>
          </div>
          <p className="max-w-sm text-sm leading-6 text-ink/80">{message ?? '加载失败，请稍后重试。'}</p>
          {onRetry ? (
            <button className="secondary-button" type="button" onClick={onRetry}>
              重试
            </button>
          ) : null}
        </>
      ) : (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-line/70 bg-cream">
            <span className="text-lg text-ink/40">—</span>
          </div>
          <p className="max-w-sm text-sm leading-6 text-ink/60">{message ?? '暂无数据'}</p>
        </>
      )}
    </div>
  )
}
