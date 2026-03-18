import { useEffect, useRef } from 'react'

type LogBufferProps = {
  messages: string[]
  maxLines?: number
  className?: string
}

export function LogBuffer({ messages, maxLines = 200, className = '' }: LogBufferProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const visibleMessages = messages.slice(-maxLines)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages])

  return (
    <div
      ref={scrollRef}
      className={`overflow-y-auto font-mono text-[11px] text-primary-foreground/50 space-y-1 ${className}`}
    >
      {visibleMessages.length === 0 ? (
        <span className="text-primary-foreground/25">等待日志...</span>
      ) : (
        visibleMessages.map((msg, i) => (
          <div key={i} className="leading-relaxed">
            <span className="text-primary-foreground/25 mr-2">{String(i + 1).padStart(3, '0')}</span>
            {msg}
          </div>
        ))
      )}
    </div>
  )
}
