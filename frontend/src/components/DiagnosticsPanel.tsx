import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { VisualDiagnostics } from '../lib/api'

const CATEGORY_LABELS: Record<string, string> = {
  brand_alignment: '品牌契合',
  visual_quality: '视觉质量',
  messaging: '信息传达',
  audience_fit: '受众匹配',
  compliance: '合规性',
}

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-gray-100 text-gray-600',
}

type DiagnosticsPanelProps = {
  diagnostics: VisualDiagnostics
  defaultExpanded?: boolean
}

export function DiagnosticsPanel({ diagnostics, defaultExpanded }: DiagnosticsPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded ?? false)

  const { issues, recommendations } = diagnostics
  if (issues.length === 0 && recommendations.length === 0) return null

  const totalIssues = issues.length

  return (
    <div className="lab-card overflow-hidden">
      <button
        type="button"
        className="flex w-full items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          )}
          <span className="text-base font-semibold text-gray-900">视觉诊断建议</span>
          {totalIssues > 0 && (
            <span className="ml-1 inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              {totalIssues}
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 px-4 pb-4 space-y-4">
          {issues.length > 0 && (
            <div className="pt-3">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">问题</h4>
              <div className="space-y-2">
                {issues.map((issue, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${SEVERITY_STYLES[issue.severity] ?? SEVERITY_STYLES.low}`}>
                      {issue.severity}
                    </span>
                    <span className="shrink-0 text-xs text-gray-400">
                      {CATEGORY_LABELS[issue.category] ?? issue.category}
                    </span>
                    <span className="text-gray-700">{issue.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {recommendations.length > 0 && (
            <div className="pt-1">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">改进建议</h4>
              <div className="space-y-2">
                {recommendations.map((rec, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${SEVERITY_STYLES[rec.priority] ?? SEVERITY_STYLES.low}`}>
                      {rec.priority}
                    </span>
                    <span className="shrink-0 text-xs text-gray-400">
                      {CATEGORY_LABELS[rec.category] ?? rec.category}
                    </span>
                    <span className="text-gray-700">{rec.action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
