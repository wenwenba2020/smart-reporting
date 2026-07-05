import { Presentation, FileText, FileType } from 'lucide-react'
import { useReportStore, type ReportType } from '@/stores/reportStore'

const REPORT_TYPES: { key: ReportType; label: string; desc: string; icon: typeof Presentation }[] = [
  { key: 'ppt', label: 'PPT 演示文稿', desc: '适合售前宣讲、工作汇报、投资人路演', icon: Presentation },
  { key: 'docx', label: 'Word 文档报告', desc: '适合详细分析报告、项目结项文档', icon: FileText },
  { key: 'pdf', label: 'PDF 正式报告', desc: '适合对外正式交付、归档留存', icon: FileType },
]

export function ReportTypeSelector() {
  const { reportType, setReportType } = useReportStore()

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">选择报告类型</h2>
      <div className="grid grid-cols-3 gap-4">
        {REPORT_TYPES.map(({ key, label, desc, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setReportType(key)}
            className={`p-6 rounded-xl border-2 text-left transition-all ${
              reportType === key
                ? 'border-primary bg-primary/5 shadow-sm'
                : 'border-border/30 hover:border-border/60 hover:bg-accent/10'
            }`}
          >
            <Icon className="w-8 h-8 mb-3 text-primary" />
            <h3 className="text-sm font-semibold">{label}</h3>
            <p className="text-[11px] text-muted-foreground mt-1">{desc}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
