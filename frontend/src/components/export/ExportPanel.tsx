import { useState } from 'react';
import { Download, FileText, Loader2, CheckCircle } from 'lucide-react';
import { useReportWorkflowStore } from '../../stores/reportWorkflowStore';
import { reportApi } from '../../api/reportClient';
import { useConfirmDialog } from '../ui/ConfirmDialog';

const EXPORT_FORMATS = [
  { key: 'pptx', label: 'PPTX', icon: FileText },
  { key: 'docx', label: 'Word', icon: FileText },
  { key: 'pdf', label: 'PDF', icon: FileText },
  { key: 'html_mindmap', label: '脑图', icon: FileText },
] as const;

export function ExportPanel({ selectedTemplateId: _selectedTemplateId }: { selectedTemplateId?: string }) {
  const [exportingFormats, setExportingFormats] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const { report, exportResults, setExportResults, confirmReport } =
    useReportWorkflowStore();

  const { confirm, dialog } = useConfirmDialog();

  const handleExport = async (formats: string[]) => {
    if (!report) return;

    setExportingFormats(new Set(formats));
    setError(null);

    try {
      const result = await reportApi.exportReport(report.report_id, formats);
      setExportResults(
        result.results.map((r) => ({
          format: r.format,
          download_url: r.download_url,
          file_path: r.file_path,
        }))
      );

      if (result.errors.length > 0) {
        setError(result.errors.map((e) => `${e.format}: ${e.error}`).join('; '));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '导出失败');
    } finally {
      setExportingFormats(new Set());
    }
  };

  const handleConfirmFirst = async (formats: string[]) => {
    if (!report) return;

    const confirmed = await confirm({
      title: '确认导出',
      message:
        '建议先确认所有章节内容后再导出。是否先确认所有章节？',
      confirmLabel: '先确认',
      cancelLabel: '直接导出',
    });

    if (confirmed) {
      try {
        await reportApi.confirmReport(report.report_id);
        confirmReport();
      } catch {
        // Continue with export even if confirm fails
      }
    }

    handleExport(formats);
  };

  const handleDownload = (downloadUrl: string) => {
    window.open(downloadUrl, '_blank');
  };

  const isExporting = exportingFormats.size > 0;

  if (!report) return null;

  return (
    <div className="flex items-center gap-2">
      {/* Export buttons */}
      {EXPORT_FORMATS.map(({ key, label, icon: Icon }) => {
        const isThisExporting = exportingFormats.has(key);
        const hasResult = exportResults.some((r) => r.format === key);
        const result = exportResults.find((r) => r.format === key);

        return (
          <div key={key} className="flex items-center gap-1">
            <button
              onClick={() => handleConfirmFirst([key])}
              disabled={isExporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/30 text-xs hover:bg-accent/30 disabled:opacity-50 transition-all"
            >
              {isThisExporting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : hasResult ? (
                <CheckCircle className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <Icon className="w-3.5 h-3.5" />
              )}
              <span>{label}</span>
            </button>
            {hasResult && result && (
              <button
                onClick={() => handleDownload(result.download_url)}
                className="p-1.5 rounded-lg text-green-600 hover:bg-green-500/10 transition-all"
                title="下载"
              >
                <Download className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        );
      })}

      {/* Export all button */}
      <button
        onClick={() =>
          handleConfirmFirst(EXPORT_FORMATS.map((f) => f.key))
        }
        disabled={isExporting}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 disabled:opacity-50 transition-all"
      >
        {isExporting ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Download className="w-3.5 h-3.5" />
        )}
        导出全部
      </button>

      {/* Error display */}
      {error && (
        <span className="text-xs text-destructive ml-2 max-w-[200px] truncate">
          {error}
        </span>
      )}

      {dialog}
    </div>
  );
}
