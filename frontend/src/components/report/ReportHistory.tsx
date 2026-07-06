import { Clock, FileText, ChevronRight } from 'lucide-react';
import { Badge } from '../ui/Badge';

export function ReportHistory() {
  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center gap-3 mb-6">
        <Clock className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold">报告历史</h1>
      </div>
      <div className="rounded-xl border border-border/30 bg-card p-12 text-center">
        <FileText className="w-16 h-16 mx-auto text-muted-foreground/30 mb-4" />
        <p className="text-sm text-muted-foreground mb-2">暂无历史报告</p>
        <p className="text-xs text-muted-foreground/70">
          生成的报告将保存在此处。在"智能报告生成"中创建您的第一份报告。
        </p>
      </div>
    </div>
  );
}
