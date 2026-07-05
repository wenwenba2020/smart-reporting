import axios from 'axios'
import type { Project, PointItem, LibraryDeck, LibrarySlide, RecommendationResult, DesignTemplate, KnowledgeBase, KnowledgeEntry, KnowledgeSearchResult, ScenarioTemplate, ScenarioDetail, ScenarioType } from '@/types/events'
import { useProjectStore } from '@/stores/projectStore'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // 不再 window.location.reload()，让 App.tsx 的 autoLogin 逻辑处理
      // 触发状态更新，让 UI 进入加载状态后自动重新登录
      useProjectStore.getState().setLoggedIn(false)
    }
    return Promise.reject(err)
  }
)

// Auth
export const login = async (username: string, password: string) => {
  const { data } = await api.post<{ access_token: string }>('/auth/login', { username, password })
  localStorage.setItem('token', data.access_token)
  return data
}
export const logout = () => {
  localStorage.removeItem('token')
  useProjectStore.getState().setLoggedIn(false)
  useProjectStore.getState().setCurrentProject(null)
}
export const autoLogin = async () => {
  const { data } = await api.post<{ access_token: string }>('/auth/login', { username: 'admin', password: 'admin123' })
  localStorage.setItem('token', data.access_token)
  return data
}
export const switchAccount = async (username: string, password: string) => {
  const { data } = await api.post<{ access_token: string }>('/auth/login', { username, password })
  localStorage.setItem('token', data.access_token)
  return data
}

// Projects
export const listProjects = () => api.get<Project[]>('/projects').then(r => r.data)
export const createProject = (name: string, template_id?: string) =>
  api.post<Project>('/projects', { name, template_id }).then(r => r.data)
export const getProject = (id: string) => api.get<Project>(`/projects/${id}`).then(r => r.data)
export const deleteProject = (id: string) => api.delete(`/projects/${id}`)

// Generation
export const triggerGeneration = (projectId: string, message: string) =>
  api.post<{ task_id: string; status: string }>(`/projects/${projectId}/generate`, { message }).then(r => r.data)

// Three-stage planning
export const planInteract = (projectId: string, params: {
  message: string; stage?: number; step?: number; positioning?: string;
  positioning_answers?: Record<string, string>;
  outline_skeleton?: unknown[]; url_context?: string;
}) => api.post(`/projects/${projectId}/plan`, params, {
  timeout: 120000, // 2 minutes for LLM calls
}).then(r => r.data)

export const planRefine = (projectId: string, params: {
  message: string; outline_skeleton?: unknown[]; url_context?: string;
}) => api.post(`/projects/${projectId}/plan/refine`, params).then(r => r.data)

export const confirmAndGenerate = (projectId: string, params: {
  message: string; outline_skeleton: unknown[];
}) => api.post(`/projects/${projectId}/confirm`, params).then(r => r.data)

// Outline
export const getOutline = (projectId: string) =>
  api.get(`/projects/${projectId}/outline`).then(r => r.data)

// Single-slide revision
export const reviseSlide = (projectId: string, slideId: string, instruction: string) =>
  api.post<{ task_id: string; status: string; slide_id: string }>(
    `/projects/${projectId}/slides/${slideId}/revise`,
    { instruction }
  ).then(r => r.data)

// Slide history (undo)
export const getSlideHistory = (projectId: string, slideId: string) =>
  api.get<{ slide_id: string; history: Array<{ timestamp: string; has_meta: boolean }> }>(
    `/projects/${projectId}/slides/${slideId}/history`
  ).then(r => r.data)

export const revertSlide = (projectId: string, slideId: string) =>
  api.post<{ task_id: string; status: string; slide_id: string }>(
    `/projects/${projectId}/slides/${slideId}/revert`
  ).then(r => r.data)

// Manual text editing (no LLM)
export interface SlideTextNode { index: number; text: string; tag: string }
export const getSlideTexts = (projectId: string, slideId: string) =>
  api.get<{ slide_id: string; texts: SlideTextNode[] }>(
    `/projects/${projectId}/slides/${slideId}/texts`
  ).then(r => r.data)

export const editSlideTexts = (projectId: string, slideId: string, edits: Array<{ index: number; new_text: string }>) =>
  api.post<{ task_id: string; status: string; slide_id: string; count: number }>(
    `/projects/${projectId}/slides/${slideId}/edit-texts`,
    { edits }
  ).then(r => r.data)

// Design templates
export const listDesignTemplates = () =>
  api.get<{ templates: DesignTemplate[] }>('/projects/design-templates').then(r => r.data)

export const getProjectDesign = (projectId: string) =>
  api.get<{ project_id: string; has_custom_design: boolean; template_id: string | null; content: string | null }>(
    `/projects/${projectId}/design`
  ).then(r => r.data)

export const applyDesignTemplate = (projectId: string, templateId: string) =>
  api.post<{ project_id: string; template_id: string; bytes_written: number }>(
    `/projects/${projectId}/design-template`,
    { template_id: templateId }
  ).then(r => r.data)

export const applyDesignToAllSlides = (projectId: string) =>
  api.post<{ task_id: string; status: string }>(
    `/projects/${projectId}/design/apply-to-all`
  ).then(r => r.data)

// Upload
export const uploadDocument = (projectId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/projects/${projectId}/upload/document`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const uploadReferencePptx = (projectId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/projects/${projectId}/upload/reference-pptx`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

// URL 调研（Tavily extract）
export interface ResearchResult {
  url: string
  status: 'ok' | 'failed'
  title?: string
  chars?: number
  preview?: string
  saved_path?: string
  error?: string
}

export type ResearchProvider = 'exa' | 'tavily'

export const researchUrls = (
  projectId: string,
  urls: string[],
  deep = false,
  provider: ResearchProvider = 'exa',
) =>
  api.post(
    `/projects/${projectId}/research`,
    { urls, deep, provider },
    { timeout: deep ? 180000 : 70000 },
  ).then(r => r.data as { results: ResearchResult[] })

// Download URL
export const getDownloadUrl = (projectId: string) => {
  const token = localStorage.getItem('token')
  return `${API_BASE}/projects/${projectId}/download?token=${token}`
}

// Content review gate
export const confirmContent = (projectId: string) =>
  api.post(`/projects/${projectId}/content/confirm`).then(r => r.data as { task_id: string; status: string })

// Slide content patch (审核态直接改 OUTLINE，不跑设计师)
export interface SlideContentPatch {
  title?: string
  subtitle?: string
  points?: PointItem[]
  notes_speaker?: string
}

export const updateSlideContent = (projectId: string, slideId: string, patch: SlideContentPatch) =>
  api.put(`/projects/${projectId}/slides/${slideId}/content`, patch).then(r => r.data as { status: string; slide_id: string })

// SSE
export const getStreamUrl = (projectId: string) => {
  const token = localStorage.getItem('token')
  return `${API_BASE}/projects/${projectId}/stream?token=${token}`
}

// Slide Library
export const uploadToLibrary = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<{ library_id: string; name: string; slide_count: number }>(
    '/library/upload', form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  ).then(r => r.data)
}

export const listLibraryDecks = () =>
  api.get<LibraryDeck[]>('/library/decks').then(r => r.data)

export const getLibraryDeck = (id: string) =>
  api.get<LibraryDeck & { slides: LibrarySlide[] }>(`/library/decks/${id}`).then(r => r.data)

export const deleteLibraryDeck = (id: string) =>
  api.delete(`/library/decks/${id}`)

export const updateLibraryDeckName = (id: string, name: string) =>
  api.patch(`/library/decks/${id}`, { name })

export const updateLibrarySlide = (id: string, data: { slide_number?: string | null; tags?: string[] }) =>
  api.patch(`/library/slides/${id}`, data).then(r => r.data)

export const searchLibrarySlides = (q?: string, tag?: string) => {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (tag) params.set('tag', tag)
  return api.get<LibrarySlide[]>(`/library/slides/search?${params.toString()}`).then(r => r.data)
}

export const importSlidesToProject = (projectId: string, slideIds: string[]) =>
  api.post<{ imported_slide_ids: string[]; total_slides: number }>(
    `/library/import-to-project/${projectId}`, { slide_ids: slideIds }
  ).then(r => r.data)

export const getRecommendedSlides = (projectId: string, limit?: number) => {
  const params = new URLSearchParams()
  if (limit) params.set('limit', String(limit))
  const qs = params.toString()
  return api.get<RecommendationResult>(
    `/library/recommend/${projectId}${qs ? '?' + qs : ''}`,
    { timeout: 30000 },
  ).then(r => r.data)
}

// Design extraction from library
export const extractLibraryDesign = (deckId: string, name?: string) =>
  api.post<{ slug: string; name: string; path: string }>(
    `/library/decks/${deckId}/extract-design`,
    { name },
  ).then(r => r.data)

export const deleteUserTemplate = (slug: string) =>
  api.delete(`/library/templates/${slug}`)

// ── Knowledge Base ─────────────────────────────────────────────

export const createKnowledgeBase = (data: { name: string; description?: string; category?: string }) =>
  api.post<{ id: string; name: string; category: string }>('/knowledge/bases', data).then(r => r.data)

export const listKnowledgeBases = () =>
  api.get<KnowledgeBase[]>('/knowledge/bases').then(r => r.data)

export const deleteKnowledgeBase = (kbId: string) =>
  api.delete(`/knowledge/bases/${kbId}`)

export const uploadToKnowledgeBase = (kbId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<{ kb_id: string; filename: string; chunks_created: number }>(
    `/knowledge/bases/${kbId}/upload`, form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  ).then(r => r.data)
}

export const searchKnowledge = (q: string, kbId?: string, category?: string, topK?: number) => {
  const params = new URLSearchParams({ q })
  if (kbId) params.set('kb_id', kbId)
  if (category) params.set('category', category)
  if (topK) params.set('top_k', String(topK))
  return api.get<{ query: string; results: KnowledgeSearchResult[] }>(
    `/knowledge/search?${params.toString()}`
  ).then(r => r.data)
}

export const listKnowledgeEntries = (kbId: string, offset = 0, limit = 50) =>
  api.get<KnowledgeEntry[]>(`/knowledge/bases/${kbId}/entries?offset=${offset}&limit=${limit}`).then(r => r.data)

// ── Case Library classify ──────────────────────────────────────

export const classifyDeck = (deckId: string, data: { scenario_type?: string; is_excellent?: boolean; tags?: string[] }) =>
  api.patch<{ id: string; scenario_type: string | null; is_excellent: boolean; tags: string[] }>(
    `/library/decks/${deckId}/classify`, data
  ).then(r => r.data)

// ── Scenarios ──────────────────────────────────────────────────

export const listScenarios = () =>
  api.get<ScenarioTemplate[]>('/scenarios').then(r => r.data)

export const getScenarioDetail = (scenarioId: string) =>
  api.get<ScenarioDetail>(`/scenarios/${scenarioId}`).then(r => r.data)

export const updateScenario = (scenarioId: string, data: Partial<ScenarioDetail>) =>
  api.put<{ id: string; name: string; updated: boolean }>(`/scenarios/${scenarioId}`, data).then(r => r.data)

export const listScenarioTypes = () =>
  api.get<{ types: ScenarioType[] }>('/scenarios/types/list').then(r => r.data)

// ── Data Sources ────────────────────────────────────────────────

export const listDataSources = () =>
  api.get<Array<{ source_type: string; source_name: string }>>('/data-sources').then(r => r.data)

export const getDataSourceSchema = (sourceType: string) =>
  api.get<{ source_type: string; source_name: string; categories: string[]; fields: string[]; total_documents: number }>(
    `/data-sources/${sourceType}/schema`
  ).then(r => r.data)

// ── Smart Fill ──────────────────────────────────────────────────

export const smartFill = (data: { query: string; report_type: string; scenario_type?: string | null; selected_sources?: string[] }) =>
  api.post<{ structured_markdown: string; report_json: Record<string, unknown>; source_references: Array<{ source_type: string; source_name: string; doc_count: number }> }>(
    '/smart-fill', data
  ).then(r => r.data)

// ── Report Templates ────────────────────────────────────────────

export const listReportTemplates = (reportType?: string) => {
  const params = reportType ? `?report_type=${reportType}` : ''
  return api.get<Array<{ id: string; name: string; report_type: string; source: string; style_rules: Record<string, unknown>; content_slots: Array<Record<string, unknown>> }>>(
    `/report-templates${params}`
  ).then(r => r.data)
}

export const uploadReportTemplate = (file: File, name?: string, reportType?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  if (reportType) form.append('report_type', reportType)
  return api.post('/report-templates/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

// ── Reports ─────────────────────────────────────────────────────

export const generateReport = (data: { report_json: Record<string, unknown>; format_type: string }) =>
  api.post<{ format: string; mime_type: string; file_size: number; download_url: string }>(
    '/reports/generate', data
  ).then(r => r.data)

export const listReportFormats = () =>
  api.get<{ formats: string[] }>('/reports/formats').then(r => r.data)

export default api
