import { List, ChevronRight, AlertTriangle, FileText } from 'lucide-react';
import { useReportWorkflowStore } from '../../stores/reportWorkflowStore';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

export function OutlineTree() {
  const { report, activeSectionKey, setActiveSection } = useReportWorkflowStore();

  if (!report) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
        return <Badge variant="confirmed">confirmed</Badge>;
      case 'draft':
        return <Badge variant="draft">draft</Badge>;
      case 'modified':
        return <Badge variant="modified">modified</Badge>;
      default:
        return <Badge variant="draft">draft</Badge>;
    }
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence < 0.5) {
      return <AlertTriangle className="w-3.5 h-3.5 text-orange-500 shrink-0" />;
    }
    return null;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border/30 flex items-center gap-2">
        <List className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-semibold">报告大纲</span>
        <span className="text-xs text-muted-foreground ml-auto">
          {report.sections.length} 章节
        </span>
      </div>

      {/* Section list */}
      <div className="flex-1 overflow-y-auto py-2">
        {report.sections.map((section, idx) => {
          const isActive = activeSectionKey === section.key;
          const isLowConfidence = section.confidence < 0.5;

          return (
            <button
              key={section.key}
              onClick={() => setActiveSection(section.key)}
              className={cn(
                'w-full text-left px-4 py-2.5 flex items-start gap-2 transition-colors border-l-2 group',
                isActive
                  ? 'border-primary bg-primary/5 text-foreground'
                  : 'border-transparent hover:bg-muted/30 text-muted-foreground hover:text-foreground',
                isLowConfidence && 'bg-yellow-500/5'
              )}
            >
              {/* Section number */}
              <span className="text-xs font-mono text-muted-foreground mt-0.5 shrink-0">
                {String(idx + 1).padStart(2, '0')}
              </span>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 shrink-0" />
                  <span className="text-sm font-medium truncate">{section.title}</span>
                </div>
                <div className="flex items-center gap-1.5 mt-1">
                  {getStatusBadge(section.status)}
                  {getConfidenceIcon(section.confidence)}
                  {section.confidence < 0.7 && section.confidence >= 0.5 && (
                    <span className="text-[10px] text-yellow-600">
                      {Math.round(section.confidence * 100)}%
                    </span>
                  )}
                </div>
                {section.slide_refs.length > 0 && (
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {section.slide_refs.length} 个案例匹配
                  </p>
                )}
              </div>

              <ChevronRight
                className={cn(
                  'w-4 h-4 mt-0.5 shrink-0 transition-transform',
                  isActive ? 'text-primary rotate-90' : 'text-muted-foreground/30'
                )}
              />
            </button>
          );
        })}
      </div>

      {/* Footer stats */}
      <div className="px-4 py-2 border-t border-border/30 text-xs text-muted-foreground space-y-1">
        <div className="flex justify-between">
          <span>已确认</span>
          <span className="text-green-600 font-medium">
            {report.sections.filter((s) => s.status === 'confirmed').length}
          </span>
        </div>
        <div className="flex justify-between">
          <span>草稿</span>
          <span>{report.sections.filter((s) => s.status === 'draft').length}</span>
        </div>
        {report.sections.filter((s) => s.confidence < 0.5).length > 0 && (
          <div className="flex justify-between">
            <span className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-orange-500" />
              低置信度
            </span>
            <span className="text-orange-600 font-medium">
              {report.sections.filter((s) => s.confidence < 0.5).length}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
