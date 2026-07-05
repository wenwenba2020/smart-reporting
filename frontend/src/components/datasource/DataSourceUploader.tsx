import { useState, useRef, useCallback } from 'react';
import { Upload, FileText, X, Sparkles, Loader2, ChevronDown } from 'lucide-react';
import { useReportWorkflowStore } from '../../stores/reportWorkflowStore';
import { reportApi, createReportSSE } from '../../api/reportClient';
import { Spinner } from '../ui/Spinner';
import { Badge } from '../ui/Badge';
import type { SSEEvent, ReportSection } from '../../types';

export function DataSourceUploader() {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<Array<{ template_id: string; name: string; category: string }>>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    uploadedSources,
    addSource,
    removeSource,
    query,
    setQuery,
    intent,
    recommendations,
    selectedTemplateId,
    setIntent,
    setSelectedTemplate,
    setReport,
    setStage,
    setIsGenerating,
    setGenerationProgress,
    setGenerationError,
    isGenerating,
    generationProgress,
    generationError,
    stage,
  } = useReportWorkflowStore();

  // ── File upload ─────────────────────────────────────────────
  const handleUpload = useCallback(
    async (files: FileList | File[]) => {
      setUploadError(null);
      setUploading(true);
      const fileArray = Array.from(files);

      for (const file of fileArray) {
        try {
          const result = await reportApi.uploadDatasource(file);
          addSource({
            source_id: result.source_id,
            title: result.title,
            source_type: result.source_type,
          });
        } catch (e) {
          setUploadError(`上传 ${file.name} 失败: ${e instanceof Error ? e.message : '未知错误'}`);
        }
      }
      setUploading(false);
    },
    [addSource]
  );

  // ── Load templates ──────────────────────────────────────────
  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    try {
      const result = await reportApi.listTemplates();
      setTemplates(result.data || []);
    } catch {
      // Templates not critical; can proceed without
    }
    setTemplatesLoading(false);
  }, []);

  // ── Recognize intent ────────────────────────────────────────
  const handleRecognizeIntent = async () => {
    if (!query.trim()) return;
    setStage('intent');
    setGenerationError(null);
    try {
      const result = await reportApi.recognizeIntent(
        query,
        uploadedSources.map((s) => s.source_id)
      );
      setIntent(result.intent, result.recommendations || []);
    } catch (e) {
      setGenerationError(e instanceof Error ? e.message : '意图识别失败');
    }
  };

  // ── Generate report (SSE) ───────────────────────────────────
  const handleGenerate = () => {
    if (!selectedTemplateId) return;

    setStage('generating');
    setIsGenerating(true);
    setGenerationError(null);
    setGenerationProgress({ message: '正在初始化...', current: 0, total: 0 });

    const sections: ReportSection[] = [];

    createReportSSE(
      {
        template_id: selectedTemplateId,
        source_ids: uploadedSources.map((s) => s.source_id),
        title: query.slice(0, 60) || '智能报告',
      },
      (event: SSEEvent) => {
        switch (event.type) {
          case 'progress':
            setGenerationProgress({
              message: event.message,
              current: event.current || 0,
              total: event.total || 0,
            });
            break;
          case 'section': {
            const sec: ReportSection = {
              key: event.key,
              title: event.title,
              content: event.content || '',
              confidence: 0.8,
              source_refs: [],
              slide_refs: [],
              children: [],
              status: 'draft',
            };
            sections.push(sec);

            // Build a partial report as sections arrive
            const partialReport = {
              report_id: '',
              template_id: selectedTemplateId,
              title: query.slice(0, 60) || '智能报告',
              meta: {
                report_type: intent?.report_type || '',
                period: intent?.period || '',
                department: '',
                author: '',
              },
              sections: [...sections],
              data_sources: uploadedSources.map((s) => s.source_id),
              key_metrics: {},
            };
            setReport(partialReport);
            break;
          }
          case 'done':
            setGenerationProgress({ message: '报告生成完成！', current: 0, total: 0 });
            setIsGenerating(false);
            // Final report already built from sections
            break;
        }
      },
      () => {
        // onDone
        setIsGenerating(false);
        setGenerationProgress({ message: '报告生成完成', current: 0, total: 0 });
      },
      (error) => {
        setIsGenerating(false);
        setGenerationError(error.message);
      }
    );
  };

  // ── Drag-and-drop handlers ──────────────────────────────────
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  };

  // ── Render ──────────────────────────────────────────────────
  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold font-display gradient-text mb-2">智能报告生成</h1>
        <p className="text-sm text-muted-foreground">
          上传数据源，输入报告主题，AI 自动匹配模板并生成报告
        </p>
      </div>

      {/* ── Upload Area ─────────────────────────────────────── */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative rounded-2xl border-2 border-dashed p-8 text-center cursor-pointer transition-all mb-6 ${
          dragOver
            ? 'border-primary bg-primary/5 shadow-[0_0_20px_var(--glow-color)]'
            : 'border-border/50 hover:border-primary/30 hover:bg-muted/20'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleUpload(e.target.files)}
        />
        <Upload className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
        <p className="text-sm font-medium mb-1">拖拽文件到此处或点击上传</p>
        <p className="text-xs text-muted-foreground">
          支持 PDF、DOCX、PPTX、TXT、Markdown 等格式
        </p>
      </div>

      {/* ── Upload Error ────────────────────────────────────── */}
      {uploadError && (
        <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2">
          <X className="w-4 h-4 shrink-0" />
          {uploadError}
          <button onClick={() => setUploadError(null)} className="ml-auto hover:opacity-70">
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* ── Uploaded Sources List ───────────────────────────── */}
      {uploadedSources.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            已上传数据源 ({uploadedSources.length})
          </h3>
          <div className="space-y-2">
            {uploadedSources.map((s) => (
              <div
                key={s.source_id}
                className="flex items-center gap-3 p-3 rounded-xl bg-card border border-border/30"
              >
                <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{s.title}</p>
                  <p className="text-xs text-muted-foreground">{s.source_type}</p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeSource(s.source_id);
                  }}
                  className="p-1 rounded hover:bg-muted transition-colors"
                >
                  <X className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Query Input ─────────────────────────────────────── */}
      <div className="mb-6">
        <label className="text-sm font-medium mb-2 block">报告主题 / 需求描述</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="例如：为长鑫存储生成 D7020 设备售前方案，重点介绍设备参数和客户案例..."
          rows={3}
          className="w-full p-4 rounded-xl border border-border/30 bg-background resize-none text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted-foreground/50"
        />
      </div>

      {/* ── Action Button ───────────────────────────────────── */}
      {stage === 'upload' && (
        <button
          onClick={handleRecognizeIntent}
          disabled={!query.trim() || uploading}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:shadow-[0_0_15px_var(--glow-color)] disabled:opacity-50 transition-all ml-auto"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />上传中...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />分析需求并匹配模板
            </>
          )}
        </button>
      )}

      {/* ── Intent & Template Recommendations ───────────────── */}
      {stage === 'intent' && intent && (
        <div className="space-y-4">
          {/* Intent summary */}
          <div className="rounded-xl border border-border/30 bg-card p-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              需求分析结果
            </h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">报告类型：</span>
                <span className="font-medium">{intent.report_type}</span>
              </div>
              <div>
                <span className="text-muted-foreground">类别：</span>
                <span className="font-medium">{intent.category}</span>
              </div>
              {intent.period && (
                <div>
                  <span className="text-muted-foreground">周期：</span>
                  <span className="font-medium">{intent.period}</span>
                </div>
              )}
              {intent.scope && (
                <div>
                  <span className="text-muted-foreground">范围：</span>
                  <span className="font-medium">{intent.scope}</span>
                </div>
              )}
            </div>
            {intent.key_themes.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {intent.key_themes.map((t, i) => (
                  <Badge key={i}>{t}</Badge>
                ))}
              </div>
            )}
          </div>

          {/* Template recommendations */}
          {recommendations.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">推荐模板</h3>
              {recommendations.map((rec) => (
                <button
                  key={rec.template_id}
                  onClick={() => setSelectedTemplate(rec.template_id)}
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    selectedTemplateId === rec.template_id
                      ? 'border-primary bg-primary/5 shadow-[0_0_10px_var(--glow-color)]'
                      : 'border-border/30 bg-card hover:border-primary/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{rec.name}</span>
                    <Badge variant="success">{Math.round(rec.match_score * 100)}% 匹配</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{rec.match_reason}</p>
                </button>
              ))}
            </div>
          )}

          {generationError && (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
              {generationError}
            </div>
          )}

          {/* Template manual picker */}
          <div className="border-t border-border/30 pt-3">
            <button
              onClick={() => {
                setShowTemplatePicker(!showTemplatePicker);
                if (!showTemplatePicker) loadTemplates();
              }}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronDown
                className={`w-4 h-4 transition-transform ${showTemplatePicker ? 'rotate-180' : ''}`}
              />
              手动选择模板
            </button>
            {showTemplatePicker && (
              <div className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                {templatesLoading ? (
                  <Spinner size="sm" className="mx-auto my-4" />
                ) : (
                  templates.map((t) => (
                    <button
                      key={t.template_id}
                      onClick={() => {
                        setSelectedTemplate(t.template_id);
                        setShowTemplatePicker(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                        selectedTemplateId === t.template_id
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-muted'
                      }`}
                    >
                      <span className="font-medium">{t.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">{t.category}</span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={!selectedTemplateId}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:shadow-[0_0_15px_var(--glow-color)] disabled:opacity-50 transition-all ml-auto"
          >
            <Sparkles className="w-4 h-4" />生成报告
          </button>
        </div>
      )}

      {/* ── Generating Progress ─────────────────────────────── */}
      {stage === 'generating' && (
        <div className="rounded-xl border border-border/30 bg-card p-6 text-center space-y-4">
          {isGenerating ? (
            <>
              <Spinner size="lg" className="mx-auto" />
              <div>
                <p className="text-sm font-medium mb-1">{generationProgress.message}</p>
                {generationProgress.total > 0 && (
                  <>
                    <div className="w-full bg-muted rounded-full h-2 mt-2 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-primary/70 to-primary h-2 rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.round(
                            (generationProgress.current / generationProgress.total) * 100
                          )}%`,
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {generationProgress.current} / {generationProgress.total}
                    </p>
                  </>
                )}
              </div>
            </>
          ) : generationError ? (
            <div className="text-center">
              <p className="text-sm text-destructive mb-3">{generationError}</p>
              <button
                onClick={handleGenerate}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm"
              >
                重试
              </button>
            </div>
          ) : (
            <div className="text-center">
              <Sparkles className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm font-medium text-green-600">报告生成完成！</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
