import type { PointItem } from '@/types/events'

export function normalizePoint(p: unknown): PointItem {
  if (typeof p === 'string') return { heading: p, body: null }
  if (p && typeof p === 'object') {
    const o = p as { heading?: unknown; body?: unknown }
    return {
      heading: typeof o.heading === 'string' ? o.heading : '',
      body: typeof o.body === 'string' ? o.body : null,
    }
  }
  return { heading: '', body: null }
}
