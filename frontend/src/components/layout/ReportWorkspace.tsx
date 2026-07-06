import { useState } from 'react';
import { useReportWorkflowStore } from '../../stores/reportWorkflowStore';
import { OutlineTree } from '../outline/OutlineTree';
import { MarkdownPreview } from '../preview/MarkdownPreview';
import { ChatPanel } from '../chat/ChatPanel';
import { ExportPanel } from '../export/ExportPanel';
import { PPTTemplateSelector } from '../ppt-template/PPTTemplateSelector';
import { PPTLibraryBrowser } from '../ppt-library/PPTLibraryBrowser';
import { Badge } from '../ui/Badge';
import type { PPTSlide } from '../../types';
import { FileText, ArrowLeft, Library, Palette, X } from 'lucide-react';

export function ReportWorkspace() {
  const { report, stage, setStage, reset } = useReportWorkflowStore();
  const [showTemplates, setShowTemplates] = useState(false);
  const [showLibrary, setShowLibrary] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  if (stage !== 'review' || !report) return null;

  const handleSelectSlides = (slides: PPTSlide[]) => {
    // Add selected slides as section references
    const store = useReportWorkflowStore.getState();
    for (const slide of slides) {
      store.addSection({
        key: `reused_${slide.slide_id}`,
        title: slide.title || `Slide ${slide.slide_index}`,
        content: slide.content_summary,
        confidence: 1.0,
        source_refs: [],
        slide_refs: [{
          slide_id: slide.slide_id,
          deck_id: slide.deck_id,
          deck_name: slide.deck_name,
          slide_index: slide.slide_index,
          title: slide.title,
          match_score: 1.0,
          accepted: true,
        }],
        children: [],
        status: 'draft',
      });
    }
    setShowLibrary(false);
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Top Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-border/30 bg-card/50 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { reset(); setStage('upload'); }}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            返回
          </button>
          <div className="h-4 w-px bg-border/50" />
          <FileText className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-semibold truncate max-w-md">{report.title}</h1>
          {report.meta.report_type && <Badge variant="default">{report.meta.report_type}</Badge>}

          {/* PPT Template selector toggle */}
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className={`flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors ${
              selectedTemplateId ? 'bg-green-100 text-green-700' : 'text-muted-foreground hover:text-foreground hover:bg-accent'
            }`}
          >
            <Palette className="w-3.5 h-3.5" />
            {selectedTemplateId ? '模板已选' : 'PPT模板'}
          </button>

          {/* Enterprise PPT library toggle */}
          <button
            onClick={() => setShowLibrary(!showLibrary)}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <Library className="w-3.5 h-3.5" />
            企业PPT库
          </button>
        </div>

        <ExportPanel selectedTemplateId={selectedTemplateId || undefined} />
      </header>

      {/* PPT Template Selector Panel */}
      {showTemplates && (
        <div className="border-b border-border/30 bg-card/50">
          <div className="flex items-center justify-between px-4 py-1 bg-accent/30">
            <span className="text-xs font-medium">选择 PPT 模板</span>
            <button onClick={() => setShowTemplates(false)} className="text-muted-foreground hover:text-foreground">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <PPTTemplateSelector
            selectedId={selectedTemplateId || undefined}
            onSelect={(id) => { setSelectedTemplateId(id); }}
          />
        </div>
      )}

      {/* PPT Library Browser Panel */}
      {showLibrary && (
        <div className="border-b border-border/30 bg-card/50" style={{ height: '320px' }}>
          <div className="flex items-center justify-between px-4 py-1 bg-accent/30">
            <span className="text-xs font-medium">企业 PPT 库 — 选择 Slide 引用</span>
            <button onClick={() => setShowLibrary(false)} className="text-muted-foreground hover:text-foreground">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="h-[calc(100%-32px)]">
            <PPTLibraryBrowser onSelectSlides={handleSelectSlides} />
          </div>
        </div>
      )}

      {/* Three-column layout */}
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 shrink-0 border-r border-border/30 bg-card/30 overflow-hidden flex flex-col">
          <OutlineTree />
        </aside>
        <main className="flex-1 overflow-hidden bg-background">
          <MarkdownPreview />
        </main>
        <aside className="w-80 shrink-0 border-l border-border/30 bg-card/30 overflow-hidden flex flex-col">
          <ChatPanel />
        </aside>
      </div>
    </div>
  );
}
