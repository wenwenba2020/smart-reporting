import { create } from 'zustand'
import type { AgentName, Project, ProjectStage, SlideItem, SlideStatus } from '@/types/events'
import type { ChatMessage, MessageCard, MessageRole } from '@/types/messages'

interface AgentState {
  name: AgentName
  status: 'idle' | 'running' | 'complete' | 'error'
  progress: number
  message: string
}

let _msgId = 0
const now = () => Date.now()

// Helper to get initial theme from localStorage or system preference
const getInitialTheme = (): 'light' | 'dark' => {
  if (typeof window === 'undefined') return 'light'
  const stored = localStorage.getItem('theme')
  if (stored === 'dark' || stored === 'light') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

interface ProjectStore {
  // Auth
  isLoggedIn: boolean
  setLoggedIn: (v: boolean) => void
  currentUser: string
  setCurrentUser: (v: string) => void

  // Theme
  theme: 'light' | 'dark'
  setTheme: (v: 'light' | 'dark') => void
  toggleTheme: () => void

  // Current project
  currentProject: Project | null
  setCurrentProject: (p: Project | null) => void

  // Project manager modal
  showProjectManager: boolean
  setShowProjectManager: (v: boolean) => void

  // Account manager modal
  showAccountManager: boolean
  setShowAccountManager: (v: boolean) => void

  // Slides
  slides: SlideItem[]
  setSlides: (s: SlideItem[]) => void
  updateSlideStatus: (slideId: string, status: SlideStatus) => void
  mergeSlideNotes: (notesBySlideId: Record<string, string>) => void
  selectedSlideId: string | null
  selectSlide: (id: string | null) => void

  // Project stage
  stage: ProjectStage | null
  setStage: (s: ProjectStage | null) => void

  // Cache-bust tokens (bumped on SSE events that mutate a slide's SVG)
  slideVersions: Record<string, number>
  bumpSlideVersion: (slideId: string) => void

  // Agents
  agents: Record<AgentName, AgentState>
  setAgentStatus: (name: AgentName, status: AgentState['status'], message?: string) => void
  setAgentProgress: (name: AgentName, progress: number, detail?: string) => void
  resetAgents: () => void

  // Chat
  messages: ChatMessage[]
  addMessage: (role: MessageRole, content: string) => void
  addCard: (role: MessageRole, card: MessageCard, contextSlideId?: string) => number
  updateCard: (id: number, card: MessageCard) => void
  clearMessages: () => void
}

const defaultAgent = (name: AgentName): AgentState => ({
  name,
  status: 'idle',
  progress: 0,
  message: '',
})

// Guard localStorage for SSR/test environments
const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('token')

export const useProjectStore = create<ProjectStore>((set) => ({
  isLoggedIn: hasToken,
  setLoggedIn: (v) => set({ isLoggedIn: v }),
  currentUser: 'admin',
  setCurrentUser: (v) => set({ currentUser: v }),

  theme: getInitialTheme(),
  setTheme: (v) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', v)
      document.documentElement.classList.toggle('dark', v === 'dark')
    }
    set({ theme: v })
  },
  toggleTheme: () => {
    const current = useProjectStore.getState().theme
    const next = current === 'light' ? 'dark' : 'light'
    useProjectStore.getState().setTheme(next)
  },

  currentProject: null,
  setCurrentProject: (p) => set({ currentProject: p }),

  showProjectManager: false,
  setShowProjectManager: (v) => set({ showProjectManager: v }),

  showAccountManager: false,
  setShowAccountManager: (v) => set({ showAccountManager: v }),

  slides: [],
  setSlides: (s) => set({ slides: s }),
  updateSlideStatus: (slideId, status) =>
    set((state) => ({
      slides: state.slides.map((s) =>
        s.slide_id === slideId ? { ...s, status } : s
      ),
    })),
  mergeSlideNotes: (notesBySlideId) =>
    set((state) => ({
      slides: state.slides.map((s) =>
        notesBySlideId[s.slide_id] !== undefined
          ? { ...s, notes_speaker: notesBySlideId[s.slide_id] }
          : s
      ),
    })),
  selectedSlideId: null,
  selectSlide: (id) => set({ selectedSlideId: id }),

  stage: null,
  setStage: (s) => set({ stage: s }),

  slideVersions: {},
  bumpSlideVersion: (slideId) =>
    set((state) => ({
      slideVersions: {
        ...state.slideVersions,
        [slideId]: (state.slideVersions[slideId] || 0) + 1,
      },
    })),

  agents: {
    planner: defaultAgent('planner'),
    copywriter: defaultAgent('copywriter'),
    designer: defaultAgent('designer'),
    effects: defaultAgent('effects'),
    editor: defaultAgent('editor'),
  },
  setAgentStatus: (name, status, message) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [name]: { ...state.agents[name], status, message: message || '' },
      },
    })),
  setAgentProgress: (name, progress, detail) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [name]: { ...state.agents[name], progress, message: detail || '' },
      },
    })),
  resetAgents: () =>
    set({
      agents: {
        planner: defaultAgent('planner'),
        copywriter: defaultAgent('copywriter'),
        designer: defaultAgent('designer'),
        effects: defaultAgent('effects'),
        editor: defaultAgent('editor'),
      },
    }),

  messages: [],
  addMessage: (role, content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { id: ++_msgId, role, timestamp: now(), kind: 'text', content },
      ],
    })),
  addCard: (role, card, contextSlideId) => {
    const id = ++_msgId
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role, timestamp: now(), contextSlideId, ...card } as ChatMessage,
      ],
    }))
    return id
  },
  updateCard: (id, card) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? ({ ...m, ...card } as ChatMessage) : m
      ),
    })),
  clearMessages: () => set({ messages: [] }),
}))
