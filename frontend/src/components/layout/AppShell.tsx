import { SideNav } from './SideNav'
import { useReportStore } from '@/stores/reportStore'
import { useReportWorkflowStore } from '@/stores/reportWorkflowStore'
import { DataSourceUploader } from '@/components/datasource/DataSourceUploader'
import { DataSourceManager } from '@/components/datasource/DataSourceManager'
import { ReportHistory } from '@/components/report/ReportHistory'
import { TemplateBrowser } from '@/components/template/TemplateBrowser'
import { SettingsPanel } from '@/components/layout/SettingsPanel'
import { ReportWorkspace } from '@/components/layout/ReportWorkspace'

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
        {navSection === 'history' && <ReportHistory />}
        {navSection === 'datasources' && <DataSourceManager />}
        {navSection === 'templates' && <TemplateBrowser />}
        {navSection === 'settings' && <SettingsPanel />}
      </main>
    </div>
  )
}
