// ── Smart Reporting API Client ─────────────────────────────────
// Uses the new /api/v1 backend endpoints (proxied via Vite)

import type {
  IntentResponse,
  ReportTemplate,
  ExportResult,
  SSEEvent,
} from '../types';

const BASE = '/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  const json = await res.json();
  // Handle various API response shapes
  if (json.code !== undefined) {
    // Wrapped: { code, msg, data }
    if (json.code !== 200) throw new Error(json.msg || 'API error');
    return json.data as T;
  }
  // Unwrapped response (matches backend patterns)
  return json as T;
}

export const reportApi = {
  // ── Health ───────────────────────────────────────────────────
  health: () => request<{ status: string }>('/health/'),

  // ── Data Sources ─────────────────────────────────────────────
  uploadDatasource: async (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${BASE}/datasources/upload`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json() as Promise<{
      source_id: string;
      title: string;
      source_type: string;
      preview: string;
      metadata: Record<string, unknown>;
    }>;
  },

  listDatasources: () =>
    request<{
      data: Array<{
        id: string;
        title: string;
        source_type: string;
        metadata: Record<string, unknown>;
      }>;
    }>('/datasources/'),

  deleteDatasource: (id: string) =>
    request<{ deleted: string }>(`/datasources/${id}`, { method: 'DELETE' }),

  // ── Templates ────────────────────────────────────────────────
  listTemplates: (category?: string) => {
    const qs = category ? `?category=${category}` : '';
    return request<{ data: ReportTemplate[] }>(`/templates/${qs}`);
  },

  // ── Reports: Intent ──────────────────────────────────────────
  recognizeIntent: (userQuery: string, sourceIds: string[]) =>
    request<IntentResponse>('/reports/intent', {
      method: 'POST',
      body: JSON.stringify({ user_query: userQuery, source_ids: sourceIds }),
    }),

  // ── Reports: Get ─────────────────────────────────────────────
  getReport: (reportId: string) =>
    request<{
      report_id: string;
      title: string;
      template_id: string;
      created_at: string;
      sections: Array<{
        key: string;
        title: string;
        content: string;
        source: string;
        data_sources: string[];
      }>;
      full_markdown: string;
    }>(`/reports/${reportId}`),

  // ── Reports: Update Section ──────────────────────────────────
  updateSection: (reportId: string, sectionKey: string, content: string) =>
    request<{ updated: string; report_id: string }>(
      `/reports/${reportId}/section/${sectionKey}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ content }),
      }
    ),

  // ── Reports: Chat Command ────────────────────────────────────
  chatCommand: (
    reportId: string,
    command: string,
    targetContext: string = ''
  ) =>
    request<{ operations: Array<Record<string, unknown>> }>(
      `/reports/${reportId}/chat-command`,
      {
        method: 'POST',
        body: JSON.stringify({ command, target_context: targetContext }),
      }
    ),

  // ── Reports: Confirm ─────────────────────────────────────────
  confirmReport: (reportId: string) =>
    request<{
      report_id: string;
      status: string;
      confirmed_sections: string[];
      confirmed_at: string;
    }>(`/reports/${reportId}/confirm`, { method: 'POST' }),

  // ── Export ───────────────────────────────────────────────────
  exportReport: (reportId: string, formats: string[]) =>
    request<{
      report_id: string;
      results: ExportResult[];
      errors: Array<{ format: string; error: string }>;
    }>(`/export/${reportId}/export`, {
      method: 'POST',
      body: JSON.stringify({ formats }),
    }),
};

// ── SSE Helper ─────────────────────────────────────────────────
export function createReportSSE(
  body: { template_id: string; source_ids: string[]; title: string },
  onEvent: (event: SSEEvent) => void,
  onDone: () => void,
  onError?: (error: Error) => void
): () => void {
  let cancelled = false;

  const controller = new AbortController();

  fetch(`${BASE}/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`SSE connection failed: ${res.status} ${text}`);
      }
      const reader = res.body?.getReader();
      if (!reader) throw new Error('No readable stream');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (cancelled) {
          reader.cancel();
          break;
        }
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE frames: data: {...}\n\n
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (!part.trim()) continue;
          const lines = part.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const jsonStr = line.slice(6);
              try {
                const event = JSON.parse(jsonStr) as SSEEvent;
                onEvent(event);
              } catch {
                // skip malformed events
              }
            }
          }
        }
      }

      if (!cancelled) onDone();
    })
    .catch((err) => {
      if (!cancelled && onError) {
        onError(err instanceof Error ? err : new Error(String(err)));
      }
    });

  return () => {
    cancelled = true;
    controller.abort();
  };
}
