import { useCallback } from 'react';
import { useReportWorkflowStore } from '../stores/reportWorkflowStore';
import { reportApi } from '../api/reportClient';

export function useUndo(reportId: string | null) {
  const pushUndo = useReportWorkflowStore((s) => s.pushUndo);
  const popUndo = useReportWorkflowStore((s) => s.popUndo);
  const updateSection = useReportWorkflowStore((s) => s.updateSection);

  const undo = useCallback(async () => {
    const entry = popUndo();
    if (!entry || !reportId) return;

    // Restore locally
    updateSection(entry.key, entry.content);

    // Sync to backend
    try {
      await reportApi.updateSection(reportId, entry.key, entry.content);
    } catch {
      // Local undo still applied even if backend sync fails
    }
  }, [reportId, popUndo, updateSection]);

  return { undo, pushUndo };
}
