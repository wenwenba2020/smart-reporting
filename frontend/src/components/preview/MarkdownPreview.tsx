import { useReportWorkflowStore } from '../../stores/reportWorkflowStore';
import { Badge } from '../ui/Badge';
import { AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';

/** Simple markdown-to-JSX rendering (bold, italic, lists, newlines) */
function renderSimpleMarkdown(text: string): React.ReactNode {
  if (!text) return null;

  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Empty line
    if (!trimmed) {
      if (inList) {
        elements.push(<div key={`endlist-${i}`} className="h-2" />);
        inList = false;
      }
      elements.push(<br key={i} />);
      continue;
    }

    // Heading
    if (trimmed.startsWith('### ')) {
      inList = false;
      elements.push(
        <h4 key={i} className="text-sm font-semibold mt-3 mb-1">
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      inList = false;
      elements.push(
        <h3 key={i} className="text-base font-semibold mt-4 mb-2">
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      continue;
    }

    // Unordered list
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!inList) inList = true;
      elements.push(
        <li key={i} className="text-sm ml-4 list-disc text-muted-foreground">
          {renderInline(trimmed.slice(2))}
        </li>
      );
      continue;
    }

    // Numbered list
    if (/^\d+[.)]\s/.test(trimmed)) {
      if (!inList) inList = true;
      elements.push(
        <li key={i} className="text-sm ml-4 list-decimal text-muted-foreground">
          {renderInline(trimmed.replace(/^\d+[.)]\s/, ''))}
        </li>
      );
      continue;
    }

    // Bold title (line that is entirely bold)
    if (trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.length > 4) {
      inList = false;
      elements.push(
        <p key={i} className="text-sm font-bold mt-2 mb-1">
          {renderInline(trimmed.slice(2, -2))}
        </p>
      );
      continue;
    }

    // Regular paragraph
    inList = false;
    elements.push(
      <p key={i} className="text-sm leading-relaxed">{renderInline(trimmed)}</p>
    );
  }

  return <div>{elements}</div>;
}

function renderInline(text: string): React.ReactNode {
  // Process **bold** and *italic*
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/^(.*?)\*\*(.+?)\*\*/);
    const italicMatch = remaining.match(/^(.*?)\*(.+?)\*/);

    if (boldMatch && (!italicMatch || boldMatch.index! <= italicMatch.index!)) {
      if (boldMatch[1]) parts.push(<span key={key++}>{boldMatch[1]}</span>);
      parts.push(<strong key={key++}>{boldMatch[2]}</strong>);
      remaining = remaining.slice(boldMatch[0].length);
    } else if (italicMatch) {
      if (italicMatch[1]) parts.push(<span key={key++}>{italicMatch[1]}</span>);
      parts.push(<em key={key++}>{italicMatch[2]}</em>);
      remaining = remaining.slice(italicMatch[0].length);
    } else {
      parts.push(<span key={key++}>{remaining}</span>);
      break;
    }
  }

  return <>{parts}</>;
}

export function MarkdownPreview() {
  const { report, activeSectionKey, setActiveSection } = useReportWorkflowStore();

  if (!report) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        选择左侧大纲章节查看内容
      </div>
    );
  }

  // If a specific section is active, show only that section
  if (activeSectionKey) {
    const section = report.sections.find((s) => s.key === activeSectionKey);
    if (!section) return null;

    const isLowConfidence = section.confidence < 0.5;

    return (
      <div className="flex flex-col h-full">
        <div className="px-6 py-4 border-b border-border/30">
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-lg font-semibold">{section.title}</h2>
            <Badge
              variant={section.status === 'confirmed' ? 'confirmed' : 'draft'}
            >
              {section.status}
            </Badge>
            {isLowConfidence && (
              <span className="flex items-center gap-1 text-xs text-orange-500">
                <AlertTriangle className="w-3 h-3" />
                {Math.round(section.confidence * 100)}%
              </span>
            )}
          </div>
          <button
            onClick={() => setActiveSection(null)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            &larr; 返回完整报告
          </button>
        </div>

        <div
          className={cn(
            'flex-1 overflow-y-auto px-6 py-4',
            isLowConfidence && 'bg-yellow-500/5'
          )}
        >
          {isLowConfidence && (
            <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-sm text-yellow-700 dark:text-yellow-400">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              此章节置信度较低，建议人工审核并修改
            </div>
          )}
          <div className="prose prose-sm max-w-none dark:prose-invert">
            {renderSimpleMarkdown(section.content)}
          </div>

          {/* Slide references */}
          {section.slide_refs.length > 0 && (
            <div className="mt-6 pt-4 border-t border-border/30">
              <h4 className="text-sm font-semibold mb-2">企业案例匹配</h4>
              <div className="space-y-2">
                {section.slide_refs.map((ref) => (
                  <div
                    key={ref.slide_id}
                    className="flex items-center gap-2 p-2 rounded-lg bg-muted/30 text-xs"
                  >
                    <span className="text-muted-foreground">{ref.deck_name}</span>
                    <span className="text-muted-foreground">/</span>
                    <span className="font-medium">{ref.title}</span>
                    <Badge variant="success" className="ml-auto">
                      {Math.round(ref.match_score * 100)}%
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Show full report
  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-border/30">
        <h2 className="text-lg font-semibold">{report.title}</h2>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant="default">{report.meta.report_type || '未分类'}</Badge>
          <span className="text-xs text-muted-foreground">
            {report.sections.length} 章节
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {report.sections.map((section) => {
          const isLowConfidence = section.confidence < 0.5;
          return (
            <div
              key={section.key}
              onClick={() => setActiveSection(section.key)}
              className={cn(
                'cursor-pointer rounded-xl p-4 border transition-all hover:border-primary/30',
                isLowConfidence
                  ? 'border-yellow-500/20 bg-yellow-500/5'
                  : 'border-border/30 bg-card'
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-semibold text-sm">{section.title}</h3>
                <Badge
                  variant={section.status === 'confirmed' ? 'confirmed' : 'draft'}
                >
                  {section.status}
                </Badge>
                {isLowConfidence && (
                  <span className="flex items-center gap-1 text-xs text-orange-500">
                    <AlertTriangle className="w-3 h-3" />
                    {Math.round(section.confidence * 100)}%
                  </span>
                )}
              </div>
              <div className="text-sm text-muted-foreground line-clamp-3">
                {section.content.slice(0, 200)}
                {section.content.length > 200 && '...'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
