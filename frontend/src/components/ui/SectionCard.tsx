import type { ReactNode } from 'react'

type SectionCardProps = {
  title: string
  eyebrow?: string
  description?: string
  action?: ReactNode
  className?: string
  contentClassName?: string
  children: ReactNode
}

export function SectionCard({
  title,
  eyebrow,
  description,
  action,
  className = '',
  contentClassName = '',
  children,
}: SectionCardProps) {
  return (
    <section
      className={`rounded-panel border border-line/80 bg-paper/95 shadow-card backdrop-blur transition-shadow duration-300 hover:shadow-paper ${className}`}
    >
      <div className="flex items-start justify-between gap-4 border-b border-line/50 px-5 py-4 sm:px-6">
        <div className="space-y-1.5">
          {eyebrow ? <p className="section-label">{eyebrow}</p> : null}
          <div>
            <h2 className="font-serif text-xl font-semibold text-coffee">{title}</h2>
            {description ? (
              <p className="mt-1.5 max-w-2xl text-sm leading-6 text-ink/70">{description}</p>
            ) : null}
          </div>
        </div>
        {action ? <div className="shrink-0 pt-0.5">{action}</div> : null}
      </div>
      <div className={`px-5 py-5 sm:px-6 ${contentClassName}`}>{children}</div>
    </section>
  )
}
