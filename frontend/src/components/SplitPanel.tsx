import { motion } from 'motion/react'
import type { ReactNode } from 'react'

type SplitPanelProps = {
  left: ReactNode
  right: ReactNode
  className?: string
}

export function SplitPanel({ left, right, className = '' }: SplitPanelProps) {
  return (
    <div className={`flex gap-6 w-full ${className}`}>
      <div className="w-2/5 shrink-0">
        {left}
      </div>
      <motion.div
        className="flex-1 min-w-0"
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: '60%', opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
      >
        {right}
      </motion.div>
    </div>
  )
}
