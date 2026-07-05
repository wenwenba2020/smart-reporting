import { SideNav } from './SideNav'
import { useReportStore } from '@/stores/reportStore'
import { useReportWorkflowStore } from '@/stores/reportWorkflowStore'
import { DataSourceUploader } from '@/components/datasource/DataSourceUploader'
import { ReportWorkspace } from '@/components/layout/ReportWorkspace'
import { Clock, Database, Layout, Settings } from 'lucide-react'

export function AppShell() {
  const { navSection } = useReportStore()
  const workflowStage = useReportWorkflowStore((s) => s.stage)

  // If a report is in review stage, show the full workspace
  if (workflowStage === 'review') {
    return <ReportWorkspace />
  }

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      <SideNav />

      <main className="flex-1 overflow-y-auto">
        {navSection === 'create' && <DataSourceUploader />}
        {navSection === 'history' && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
            <Clock className="w-12 h-12 opacity-20" />
            <p className="text-sm">报告历史功能即将上线</p>
          </div>
        )}
        {navSection === 'datasources' && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
            <Database className="w-12 h-12 opacity-20" />
            <p className="text-sm">数据源管理功能即将上线</p>
          </div>
        )}
        {navSection === 'templates' && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
            <Layout className="w-12 h-12 opacity-20" />
            <p className="text-sm">模板管理功能即将上线</p>
          </div>
        )}
        {navSection === 'settings' && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
            <Settings className="w-12 h-12 opacity-20" />
            <p className="text-sm">系统设置功能即将上线</p>
          </div>
        )}
      </main>
    </div>
  )
}
