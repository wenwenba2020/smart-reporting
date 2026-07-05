// ── Smart Reporting Domain Types ─────────────────────────────────

export interface SourceDocument {
  source_id: string;
  source_type: string;
  title: string;
  content: string;
  metadata: Record<string, unknown>;
}

export interface ReportTemplate {
  template_id: string;
  name: string;
  category: string;
  description: string;
  sections: SectionDef[];
  system_prompt: string;
}

export interface SectionDef {
  key: string;
  title: string;
  required: boolean;
  description: string;
  source: string;
  suggested_length: string;
}

export interface ReportIntent {
  report_type: string;
  category: string;
  period: string;
  scope: string;
  key_themes: string[];
}

export interface TemplateRecommendation {
  template_id: string;
  name: string;
  match_score: number;
  match_reason: string;
  is_selected: boolean;
}

export interface ReportSection {
  key: string;
  title: string;
  content: string;
  confidence: number;
  source_refs: string[];
  slide_refs: SlideRef[];
  children: ReportSection[];
  status: string;
}

export interface SlideRef {
  slide_id: string;
  deck_id: string;
  deck_name: string;
  slide_index: number;
  title: string;
  match_score: number;
  accepted: boolean;
}

export interface StructuredReport {
  report_id: string;
  template_id: string;
  title: string;
  meta: ReportMeta;
  sections: ReportSection[];
  data_sources: string[];
  key_metrics: Record<string, unknown>;
}

export interface ReportMeta {
  report_type: string;
  period: string;
  department: string;
  author: string;
}

export interface ExportResult {
  file_path: string;
  file_size: number;
  format: string;
  download_url: string;
}

// ── API Response Wrappers ──────────────────────────────────────

export interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T;
}

export interface IntentResponse {
  intent: ReportIntent;
  recommendations: TemplateRecommendation[];
}

// ── SSE Event Types ───────────────────────────────────────────

export interface SSEProgressEvent {
  type: 'progress';
  phase: string;
  message: string;
  done?: boolean;
  current?: number;
  total?: number;
}

export interface SSESectionEvent {
  type: 'section';
  key: string;
  title: string;
  content: string;
  index: number;
}

export interface SSEValidationEvent {
  type: 'validation';
  // validation result fields
  [key: string]: unknown;
}

export interface SSESlideMatchEvent {
  type: 'slide_matches';
  matches: Record<string, Array<{ title: string; score: number }>>;
}

export interface SSEDoneEvent {
  type: 'done';
  report_id: string;
  title: string;
  section_count: number;
}

export type SSEEvent =
  | SSEProgressEvent
  | SSESectionEvent
  | SSEValidationEvent
  | SSESlideMatchEvent
  | SSEDoneEvent;
