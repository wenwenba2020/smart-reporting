import { FileText, Clock, Database, Layout, Settings } from 'lucide-react'
import { useReportStore, type NavSection } from '@/stores/reportStore'

const NAV_ITEMS: { key: NavSection; label: string; icon: typeof FileText }[] = [
  { key: 'create', label: '新建报告', icon: FileText },
  { key: 'history', label: '报告历史', icon: Clock },
  { key: 'datasources', label: '数据源', icon: Database },
  { key: 'templates', label: '模板管理', icon: Layout },
  { key: 'settings', label: '系统设置', icon: Settings },
]

export function SideNav() {
  const { navSection, setNav } = useReportStore()

  return (
    <nav className="w-56 h-full flex flex-col border-r border-border/30 bg-card/30 shrink-0">
      <div className="p-4 border-b border-border/30">
        <h1 className="text-sm font-bold tracking-tight">📊 智能报告平台</h1>
        <p className="text-[10px] text-muted-foreground mt-0.5">Enterprise Report Studio</p>
      </div>
      <div className="flex-1 p-2 space-y-1">
        {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setNav(key)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
              navSection === key
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground hover:bg-accent/30 hover:text-foreground'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>
    </nav>
  )
}
