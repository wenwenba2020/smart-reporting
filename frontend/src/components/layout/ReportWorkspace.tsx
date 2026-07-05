import { useReportWorkflowStore } from '../../stores/reportWorkflowStore';
import { OutlineTree } from '../outline/OutlineTree';
import { MarkdownPreview } from '../preview/MarkdownPreview';
import { ChatPanel } from '../chat/ChatPanel';
import { ExportPanel } from '../export/ExportPanel';
import { Badge } from '../ui/Badge';
import { FileText, ArrowLeft } from 'lucide-react';

export function ReportWorkspace() {
  const { report, stage, setStage, reset } = useReportWorkflowStore();

  if (stage !== 'review' || !report) return null;

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Top Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-border/30 bg-card/50 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              reset();
              setStage('upload');
            }}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            返回
          </button>
          <div className="h-4 w-px bg-border/50" />
          <FileText className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-semibold truncate max-w-md">
            {report.title}
          </h1>
          {report.meta.report_type && (
            <Badge variant="default">{report.meta.report_type}</Badge>
          )}
        </div>

        <ExportPanel />
      </header>

      {/* Three-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Outline Tree */}
        <aside className="w-64 shrink-0 border-r border-border/30 bg-card/30 overflow-hidden flex flex-col">
          <OutlineTree />
        </aside>

        {/* Center: Markdown Preview */}
        <main className="flex-1 overflow-hidden bg-background">
          <MarkdownPreview />
        </main>

        {/* Right: Chat Panel */}
        <aside className="w-80 shrink-0 border-l border-border/30 bg-card/30 overflow-hidden flex flex-col">
          <ChatPanel />
        </aside>
      </div>
    </div>
  );
}
