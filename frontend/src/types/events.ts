export type AgentName = 'planner' | 'copywriter' | 'designer' | 'effects' | 'editor'
export type SlideStatus = 'todo' | 'generating' | 'done' | 'locked' | 'failed'

export type ProjectStage =
  | 'idle'
  | 'planning'
  | 'copywriting'
  | 'awaiting_content_review'
  | 'designing'
  | 'completed'
  | 'failed'

export type SSEEvent =
  | { type: 'agent_start'; agent: AgentName; message: string }
  | { type: 'agent_progress'; agent: AgentName; progress: number; detail: string }
  | { type: 'agent_complete'; agent: AgentName; output_ref?: string }
  | { type: 'slide_status_change'; slide_id: string; status: SlideStatus }
  | { type: 'confirmation_required'; confirmation_type: 'outline' | 'diagnosis'; payload: unknown }
  | { type: 'generation_complete'; export_url: string }
  | { type: 'content_ready' }
  | { type: 'stage_change'; stage: ProjectStage }
  | { type: 'slide_content_changed'; slide_id: string }
  | { type: 'error'; agent: AgentName; message: string; recoverable: boolean }

export interface PointItem {
  heading: string
  body?: string | null
}

export interface Project {
  id: string
  name: string
  status: string
  template_id: string | null
  total_slides: number
  stage?: ProjectStage
}

export interface SlideItem {
  slide_id: string
  title: string
  layout: string
  status: SlideStatus
  points: PointItem[]
  locked: boolean
  notes_speaker?: string
}

// Slide Library types
export interface LibraryDeck {
  id: string
  name: string
  original_filename: string
  slide_count: number
  created_at: string
  updated_at: string
}

export interface LibrarySlide {
  id: string
  library_id: string
  slide_index: number
  slide_number: string | null
  title: string
  text_summary: string
  tags: string[]
  thumbnail_url: string
  layout_hint: string
}

// Slide recommendation
export interface RecommendedSlide extends LibrarySlide {
  score: number
}

export interface RecommendationResult {
  project_id: string
  recommendations: RecommendedSlide[]
  error?: string
}

// Design template (extended with source field)
export interface DesignTemplate {
  id: string
  name: string
  subtitle: string
  description: string
  colors: Array<{ role: string; hex: string }>
  source?: 'builtin' | 'user'
}

// ── Knowledge Base types ──────────────────────────────────────

export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  category: 'product' | 'customer' | 'meeting' | 'general'
  entry_count: number
  created_at: string
}

export interface KnowledgeEntry {
  id: string
  kb_id: string
  title: string
  content_preview: string
  source_name: string
  chunk_index: number
  created_at: string
}

export interface KnowledgeSearchResult {
  id: string
  kb_id: string
  title: string
  content: string
  source_name: string
  score: number
  metadata: Record<string, unknown>
}

// ── Scenario types ────────────────────────────────────────────

export interface ScenarioTemplate {
  id: string
  name: string
  scenario_type: 'presales' | 'investor' | 'review' | 'report' | 'channel'
  description: string
  icon: string | null
  slide_count: number
  is_preset: boolean
  sort_order: number
}

export interface ScenarioDetail extends ScenarioTemplate {
  slide_framework: Array<{
    seq: number
    role: string
    layout: string
    prompt_hint: string
  }>
  data_source_hints: string | null
  talk_track_templates: Record<string, string> | null
  is_active: boolean
}

export interface ScenarioType {
  key: string
  label: string
  icon: string
}
