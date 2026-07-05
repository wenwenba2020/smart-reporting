import type { AgentName, PointItem, SlideItem } from './events'

export type MessageRole = 'user' | 'assistant' | 'system'

export interface OutlineSlide {
  slide_id: string
  title: string
  layout: string
  subtitle?: string
  points?: PointItem[]
  [key: string]: unknown
}

export type MessageCard =
  | { kind: 'text'; content: string }
  | {
      kind: 'question'
      question: string
      options: string[]
      recommendation?: string
      keyName: string
      answered?: string
    }
  | { kind: 'outline'; slides: OutlineSlide[]; stage: 2 | 3 }
  | { kind: 'agent-work'; taskId: string; liveRef: true }
  | {
      kind: 'agent-handoff'
      fromAgent: AgentName
      toAgent: AgentName
      detail: string
    }
  | { kind: 'generation-complete'; projectId: string }
  | { kind: 'slide-ref'; slideId: string; title: string }
  | {
      kind: 'slide-diff'
      slideId: string
      beforeSvgUrl: string
      afterSvgUrl: string
      status: 'pending' | 'accepted' | 'rejected'
    }
  | { kind: 'upload'; filename: string; preview?: string }
  | {
      kind: 'error'
      message: string
      agent?: AgentName
      recoverable: boolean
    }
  | {
      kind: 'archived-subchat'
      slideId: string
      messages: ChatMessage[]
      summary: string
    }
  | { kind: 'stage-indicator'; fromStage: number; toStage: number }

export type ChatMessage = {
  id: number
  role: MessageRole
  timestamp: number
  contextSlideId?: string
} & MessageCard

export function isTextMessage(msg: ChatMessage): msg is ChatMessage & { kind: 'text' } {
  return msg.kind === 'text'
}

// Convert SlideItem to OutlineSlide for outline card display
export function slideItemToOutline(s: SlideItem): OutlineSlide {
  return {
    slide_id: s.slide_id,
    title: s.title,
    layout: s.layout,
    points: s.points,
  }
}
