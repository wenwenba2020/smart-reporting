import { useEffect, useRef } from 'react'
import { useProjectStore } from '@/stores/projectStore'
import { getStreamUrl, getOutline } from '@/api/client'
import type { SlideItem, SlideStatus } from '@/types/events'
import { normalizePoint } from '@/utils/normalizePoint'

const AGENT_LABELS: Record<string, string> = {
  planner: '规划师', copywriter: '文案师', designer: '设计师',
  effects: '效果师', editor: '编辑师',
}

const VALID_STATUS: SlideStatus[] = ['todo', 'generating', 'done', 'locked', 'failed']

async function refreshNotes(projectId: string) {
  try {
    const data = await getOutline(projectId)
    const notes: Record<string, string> = {}
    for (const s of data.slides || []) {
      if (s.slide_id && typeof s.notes_speaker === 'string') {
        notes[s.slide_id] = s.notes_speaker
      }
    }
    if (Object.keys(notes).length > 0) {
      useProjectStore.getState().mergeSlideNotes(notes)
    }
  } catch (err) {
    console.warn('[SSE] refreshNotes failed:', err)
  }
}

async function loadInitialSlides(projectId: string) {
  try {
    const data = await getOutline(projectId)
    const slides: SlideItem[] = (data.slides || []).map((s: Record<string, unknown>) => ({
      slide_id: String(s.slide_id ?? ''),
      title: String(s.title ?? ''),
      layout: String(s.layout ?? ''),
      status: VALID_STATUS.includes(s.status as SlideStatus) ? (s.status as SlideStatus) : 'todo',
      points: Array.isArray(s.points) ? (s.points as unknown[]).map(normalizePoint) : [],
      locked: Boolean(s.locked),
      notes_speaker: typeof s.notes_speaker === 'string' ? s.notes_speaker : '',
    }))
    // Always update slides, even if empty (e.g., new project without outline)
    useProjectStore.getState().setSlides(slides)
  } catch {
    // 404 when outline not yet confirmed — clear slides for new project
    useProjectStore.getState().setSlides([])
  }
}

export function useSSE(projectId: string | null) {
  const sourceRef = useRef<EventSource | null>(null)
  const store = useProjectStore

  useEffect(() => {
    if (!projectId) return

    loadInitialSlides(projectId)

    const url = getStreamUrl(projectId)
    const es = new EventSource(url)
    sourceRef.current = es

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        const s = store.getState()

        switch (event.type) {
          case 'agent_start':
            s.setAgentStatus(event.agent, 'running', event.message)
            break
          case 'agent_progress':
            s.setAgentProgress(event.agent, event.progress, event.detail)
            break
          case 'agent_complete':
            s.setAgentStatus(event.agent, 'complete')
            if (event.agent === 'copywriter' && projectId) {
              refreshNotes(projectId)
            }
            break
          case 'agent_handoff': {
            const from = AGENT_LABELS[event.from_agent] || event.from_agent
            const to = AGENT_LABELS[event.to_agent] || event.to_agent
            s.addMessage('assistant', `🔄 ${from} → ${to}：${event.detail}`)
            break
          }
          case 'agent_thinking': {
            const agentName = event.agent as keyof typeof s.agents
            const currentStatus = s.agents[agentName]?.status || 'running'
            s.setAgentStatus(event.agent, currentStatus, event.thought)
            break
          }
          case 'slide_status_change':
            s.updateSlideStatus(event.slide_id, event.status)
            // When a slide settles to 'done', the SVG on disk has been rewritten —
            // bump its cache-bust version so the thumbnail re-fetches fresh bytes.
            if (event.status === 'done' && event.slide_id) {
              s.bumpSlideVersion(event.slide_id)
            }
            break
          case 'slide_revised':
          case 'slide_reverted':
          case 'slide_text_edited':
            if (event.slide_id) s.bumpSlideVersion(event.slide_id)
            break
          case 'generation_complete':
            s.addMessage('assistant', `🎉 PPT 生成完成！点击右侧"下载 PPTX"获取文件`)
            if (projectId) refreshNotes(projectId)
            break
          case 'content_ready':
            if (projectId) {
              loadInitialSlides(projectId)
              refreshNotes(projectId)
            }
            break
          case 'stage_change':
            s.setStage(event.stage)
            break
          case 'slide_content_changed':
            if (projectId) loadInitialSlides(projectId)
            break
          case 'error':
            s.setAgentStatus(event.agent, 'error', event.message)
            s.addMessage('assistant', `❌ [${AGENT_LABELS[event.agent] || event.agent}]: ${event.message}`)
            break
        }
      } catch (err) {
        console.warn('[SSE] Parse error:', e.data, err)
      }
    }

    es.onerror = () => {
      console.warn('[SSE] Connection error, auto-reconnecting...')
    }

    return () => {
      es.close()
      sourceRef.current = null
    }
  }, [projectId])
}
