import { create } from 'zustand';
import type {
  ReportIntent,
  TemplateRecommendation,
  StructuredReport,
} from '../types';

export type WorkflowStage =
  | 'upload'      // Uploading sources
  | 'intent'      // Showing intent + template recommendations
  | 'generating'  // SSE streaming generation in progress
  | 'review'      // Reviewing generated report
  | 'exporting';  // Export in progress

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ReportWorkflowState {
  // ── Workflow stage ───────────────────────────────────────────
  stage: WorkflowStage;
  setStage: (stage: WorkflowStage) => void;

  // ── Data sources ─────────────────────────────────────────────
  uploadedSources: Array<{
    source_id: string;
    title: string;
    source_type: string;
  }>;
  addSource: (source: { source_id: string; title: string; source_type: string }) => void;
  removeSource: (sourceId: string) => void;
  clearSources: () => void;

  // ── User query ───────────────────────────────────────────────
  query: string;
  setQuery: (q: string) => void;

  // ── Intent & templates ───────────────────────────────────────
  intent: ReportIntent | null;
  recommendations: TemplateRecommendation[];
  selectedTemplateId: string | null;
  setIntent: (intent: ReportIntent, recs: TemplateRecommendation[]) => void;
  setSelectedTemplate: (id: string) => void;

  // ── Report ───────────────────────────────────────────────────
  report: StructuredReport | null;
  setReport: (report: StructuredReport) => void;
  updateSection: (key: string, content: string) => void;
  activeSectionKey: string | null;
  setActiveSection: (key: string | null) => void;
  selectedText: string;
  setSelectedText: (text: string) => void;
  confirmReport: () => void;

  // ── Generation progress ──────────────────────────────────────
  isGenerating: boolean;
  setIsGenerating: (v: boolean) => void;
  generationProgress: { message: string; current: number; total: number };
  setGenerationProgress: (p: { message: string; current: number; total: number }) => void;
  generationError: string | null;
  setGenerationError: (e: string | null) => void;

  // ── Chat ─────────────────────────────────────────────────────
  chatMessages: ChatMessage[];
  addChatMessage: (role: 'user' | 'assistant', content: string) => void;
  clearChat: () => void;

  // ── Export results ───────────────────────────────────────────
  exportResults: Array<{ format: string; download_url: string; file_path: string }>;
  setExportResults: (results: Array<{ format: string; download_url: string; file_path: string }>) => void;

  // ── Undo history ─────────────────────────────────────────────
  undoStack: Array<{ key: string; content: string }>;
  pushUndo: (key: string, content: string) => void;
  popUndo: () => { key: string; content: string } | null;
  clearUndo: () => void;

  // ── Reset ────────────────────────────────────────────────────
  reset: () => void;
}

let msgCounter = 0;
function nextMsgId(): string {
  return `msg_${++msgCounter}_${Date.now()}`;
}

const initialGenerationProgress = { message: '', current: 0, total: 0 };

export const useReportWorkflowStore = create<ReportWorkflowState>((set, get) => ({
  stage: 'upload',
  setStage: (stage) => set({ stage }),

  uploadedSources: [],
  addSource: (source) =>
    set((s) => ({ uploadedSources: [...s.uploadedSources, source] })),
  removeSource: (sourceId) =>
    set((s) => ({
      uploadedSources: s.uploadedSources.filter((u) => u.source_id !== sourceId),
    })),
  clearSources: () => set({ uploadedSources: [] }),

  query: '',
  setQuery: (q) => set({ query: q }),

  intent: null,
  recommendations: [],
  selectedTemplateId: null,
  setIntent: (intent, recs) =>
    set({
      intent,
      recommendations: recs,
      selectedTemplateId: recs.length > 0 ? recs[0].template_id : null,
      stage: 'intent',
    }),
  setSelectedTemplate: (id) => set({ selectedTemplateId: id }),

  report: null,
  setReport: (report) => set({ report, stage: 'review' }),
  updateSection: (key, content) =>
    set((s) => {
      if (!s.report) return s;
      const sections = s.report.sections.map((sec) =>
        sec.key === key ? { ...sec, content } : sec
      );
      return { report: { ...s.report, sections } };
    }),
  activeSectionKey: null,
  setActiveSection: (key) => set({ activeSectionKey: key }),
  selectedText: '',
  setSelectedText: (text) => set({ selectedText: text }),
  confirmReport: () =>
    set((s) => {
      if (!s.report) return s;
      const sections = s.report.sections.map((sec) => ({
        ...sec,
        status: 'confirmed',
      }));
      return { report: { ...s.report, sections } };
    }),

  isGenerating: false,
  setIsGenerating: (v) => set({ isGenerating: v }),
  generationProgress: initialGenerationProgress,
  setGenerationProgress: (p) => set({ generationProgress: p }),
  generationError: null,
  setGenerationError: (e) => set({ generationError: e }),

  chatMessages: [],
  addChatMessage: (role, content) =>
    set((s) => ({
      chatMessages: [
        ...s.chatMessages,
        { id: nextMsgId(), role, content, timestamp: Date.now() },
      ],
    })),
  clearChat: () => set({ chatMessages: [] }),

  exportResults: [],
  setExportResults: (results) => set({ exportResults: results }),

  undoStack: [],
  pushUndo: (key, content) =>
    set((s) => ({ undoStack: [...s.undoStack, { key, content }] })),
  popUndo: () => {
    const stack = get().undoStack;
    if (stack.length === 0) return null;
    const entry = stack[stack.length - 1];
    set({ undoStack: stack.slice(0, -1) });
    return entry;
  },
  clearUndo: () => set({ undoStack: [] }),

  reset: () =>
    set({
      stage: 'upload',
      uploadedSources: [],
      query: '',
      intent: null,
      recommendations: [],
      selectedTemplateId: null,
      report: null,
      activeSectionKey: null,
      selectedText: '',
      isGenerating: false,
      generationProgress: initialGenerationProgress,
      generationError: null,
      chatMessages: [],
      exportResults: [],
      undoStack: [],
    }),
}));
