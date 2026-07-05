import { useState } from 'react'
import { ArrowRight, ArrowLeft, Sparkles, Loader2 } from 'lucide-react'
import { useReportStore } from '@/stores/reportStore'
import { ReportTypeSelector } from './ReportTypeSelector'
import { DataSourceSelector } from './DataSourceSelector'
import { ScenarioSelector } from '@/components/ScenarioSelector'
import { smartFill } from '@/api/client'

const STEPS = ['报告类型', '方案框架', '数据源', '生成']

export function CreateReportWizard() {
  const [step, setStep] = useState(0)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<{
    structured_markdown: string
    report_json: Record<string, unknown>
    source_references: Array<{ source_type: string; source_name: string; doc_count: number }>
  } | null>(null)
  const { reportType, selectedSources, query, setQuery } = useReportStore()

  const handleGenerate = async () => {
    if (!query.trim()) return
    setGenerating(true)
    try {
      const data = await smartFill({
        query,
        report_type: reportType,
        selected_sources: selectedSources,
      })
      setResult(data)
      setStep(3)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert(err?.response?.data?.detail || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
              i <= step ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
            }`}>{i + 1}</div>
            <span className={`text-sm ${i <= step ? 'font-medium' : 'text-muted-foreground'}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="w-8 h-px bg-border" />}
          </div>
        ))}
      </div>

      {/* Step 0: Report type + topic */}
      {step === 0 && (
        <div className="space-y-6">
          <ReportTypeSelector />
          <div className="mt-6">
            <label className="text-sm font-medium mb-2 block">报告主题</label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="例如：为长鑫存储生成 D7020 设备售前方案，重点介绍设备参数和客户案例..."
              className="w-full h-28 p-4 rounded-xl border border-border/30 bg-background resize-none text-sm outline-none focus:border-primary/30"
            />
          </div>
          <button onClick={() => setStep(1)}
            disabled={!query.trim()}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 ml-auto">
            下一步 <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Step 1: Scenario selection */}
      {step === 1 && (
        <div className="space-y-6">
          <ScenarioSelector />
          <div className="flex items-center gap-3 justify-between mt-6">
            <button onClick={() => setStep(0)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-4 h-4" />上一步
            </button>
            <button onClick={() => setStep(2)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium">
              下一步 <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Data source selection */}
      {step === 2 && (
        <div className="space-y-6">
          <DataSourceSelector />
          <div className="flex items-center gap-3 justify-between mt-6">
            <button onClick={() => setStep(1)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-4 h-4" />上一步
            </button>
            <button onClick={handleGenerate} disabled={generating}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50">
              {generating ? <><Loader2 className="w-4 h-4 animate-spin" />生成中...</> : <><Sparkles className="w-4 h-4" />生成报告</>}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Result preview */}
      {step === 3 && result && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-green-600">
            <Sparkles className="w-4 h-4" />
            智能填报完成 — 从 {result.source_references.length} 个数据源检索到相关内容
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-border/30 bg-card">
              <h3 className="text-sm font-semibold mb-2">结构化文档 (Markdown)</h3>
              <pre className="text-xs whitespace-pre-wrap max-h-[500px] overflow-y-auto font-mono">
                {result.structured_markdown.slice(0, 2000)}...
              </pre>
            </div>
            <div className="p-4 rounded-xl border border-border/30 bg-card">
              <h3 className="text-sm font-semibold mb-2">报表数据 (JSON)</h3>
              <pre className="text-xs whitespace-pre-wrap max-h-[500px] overflow-y-auto font-mono">
                {JSON.stringify(result.report_json, null, 2).slice(0, 2000)}...
              </pre>
            </div>
          </div>
          <div className="flex gap-3">
            {(['pptx', 'docx', 'pdf'] as const).map(fmt => (
              <button key={fmt}
                className="px-4 py-2 rounded-lg border border-border/30 text-sm hover:bg-accent/30">
                导出 {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
