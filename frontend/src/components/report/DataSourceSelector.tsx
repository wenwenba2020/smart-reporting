import { useEffect, useState } from 'react'
import { Check } from 'lucide-react'
import { useReportStore } from '@/stores/reportStore'
import { listDataSources, getDataSourceSchema } from '@/api/client'

interface SourceInfo {
  source_type: string
  source_name: string
  categories: string[]
  total_documents: number
}

export function DataSourceSelector() {
  const { selectedSources, toggleSource } = useReportStore()
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      setLoading(true)
      try {
        const configs = await listDataSources()
        const detailed = await Promise.all(
          configs.map(async (c: { source_type: string; source_name: string }) => {
            try {
              return await getDataSourceSchema(c.source_type)
            } catch {
              return { source_type: c.source_type, source_name: c.source_name, categories: [], total_documents: 0 }
            }
          })
        )
        setSources(detailed)
      } catch { /* empty */ } finally { setLoading(false) }
    })()
  }, [])

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">选择数据源</h2>
      <p className="text-xs text-muted-foreground mb-4">勾选需要用于本报告的数据源，AI 将自动检索相关内容</p>

      {loading ? (
        <p className="text-sm text-muted-foreground">加载中...</p>
      ) : (
        <div className="space-y-3">
          {sources.map((s) => (
            <button
              key={s.source_type}
              onClick={() => toggleSource(s.source_type)}
              className={`w-full text-left p-4 rounded-xl border transition-all flex items-center justify-between ${
                selectedSources.includes(s.source_type)
                  ? 'border-primary/40 bg-primary/5'
                  : 'border-border/20 hover:bg-accent/10'
              }`}
            >
              <div>
                <p className="text-sm font-medium">{s.source_name}</p>
                <div className="flex items-center gap-2 mt-1">
                  {s.categories.map(c => (
                    <span key={c} className="text-[10px] bg-muted px-1.5 py-0.5 rounded">{c}</span>
                  ))}
                  <span className="text-[10px] text-muted-foreground">{s.total_documents} 条记录</span>
                </div>
              </div>
              <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                selectedSources.includes(s.source_type)
                  ? 'bg-primary border-primary text-primary-foreground'
                  : 'border-muted-foreground/30'
              }`}>
                {selectedSources.includes(s.source_type) && <Check className="w-3 h-3" />}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
