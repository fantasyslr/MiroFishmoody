import { useEffect, useState } from 'react'
import { getRaceHistory } from '../lib/api'
import { CheckCircle2, CircleDashed, Clock } from 'lucide-react'

type RunRecord = {
  id: string
  date: string
  plans_count: number
  top_recommendation: string
  status: string
  hit: boolean | null
}

export function HistoryPage() {
  const [history, setHistory] = useState<{ runs: RunRecord[] } | null>(null)

  useEffect(() => {
    getRaceHistory().then(setHistory)
  }, [])

  if (!history) return <div className="p-6">正在加载历史记录...</div>

  return (
    <div className="space-y-12">
      <section className="space-y-4">
        <h1 className="font-display text-4xl text-primary font-semibold">历史记录</h1>
        <p className="text-muted-foreground text-lg max-w-2xl text-balance">
          过往评估记录及其真实投放结果。
        </p>
      </section>

      <div className="space-y-4">
        {history.runs.map((run: RunRecord) => (
          <div key={run.id} className="lab-card p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 hover:bg-black/5 transition-colors cursor-pointer">
            <div className="flex items-center gap-6">
              <div className="flex flex-col items-center justify-center w-12 h-12 rounded-sm bg-secondary text-secondary-foreground font-mono text-sm font-medium shrink-0">
                {run.id.replace('run_', '#')}
              </div>
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="text-lg font-semibold">{run.top_recommendation}</h3>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                  <span>{new Date(run.date).toLocaleDateString()}</span>
                  <span>&bull;</span>
                  <span>{run.plans_count} 个方案已评估</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-8 w-full md:w-auto border-t border-border md:border-none pt-4 md:pt-0">
              <div className="flex-1 md:flex-none">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">状态</div>
                <div className="flex items-center gap-1.5 text-sm font-medium">
                  {run.status === 'verified' ? (
                    <><CheckCircle2 className="h-4 w-4 text-green-600" /> 已验证</>
                  ) : (
                    <><Clock className="h-4 w-4 text-muted-foreground" /> 待验证</>
                  )}
                </div>
              </div>
              
              <div className="flex-1 md:flex-none">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">经验匹配</div>
                <div className="flex items-center gap-1.5 text-sm font-medium">
                  {run.hit === true ? (
                    <span className="baseline-tag bg-green-100 text-green-800">准确</span>
                  ) : run.hit === false ? (
                    <span className="baseline-tag bg-red-100 text-red-800">偏离</span>
                  ) : (
                    <><CircleDashed className="h-4 w-4 text-muted-foreground" /> N/A</>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
