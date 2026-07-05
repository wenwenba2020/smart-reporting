import { useEffect, useCallback } from 'react'
import { X, Hash, Layout } from 'lucide-react'
import type { LibrarySlide } from '@/types/events'

interface Props {
  slide: LibrarySlide | null
  onClose: () => void
}

export function SlidePreviewModal({ slide, onClose }: Props) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    if (slide) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
      return () => {
        document.removeEventListener('keydown', handleKeyDown)
        document.body.style.overflow = ''
      }
    }
  }, [slide, handleKeyDown])

  if (!slide) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border/30 rounded-2xl shadow-2xl max-w-4xl w-[90vw] max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-border/30 shrink-0">
          <h3 className="text-base font-semibold flex-1 truncate">{slide.title}</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-accent/30 text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-[1fr_300px] gap-6">
            {/* Large thumbnail */}
            <div className="bg-muted/20 rounded-xl border border-border/20 overflow-hidden">
              {slide.thumbnail_url ? (
                <img
                  src={slide.thumbnail_url}
                  alt={slide.title}
                  className="w-full h-auto"
                />
              ) : (
                <div className="aspect-video flex items-center justify-center text-muted-foreground text-sm">
                  (无缩略图)
                </div>
              )}
            </div>

            {/* Meta panel */}
            <div className="space-y-4">
              {/* Slide number */}
              <div className="flex items-center gap-2 text-sm">
                <Hash className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-muted-foreground">编号</span>
                <span className="font-mono font-medium">
                  {slide.slide_number || `#${slide.slide_index}`}
                </span>
              </div>

              {/* Layout hint */}
              <div className="flex items-center gap-2 text-sm">
                <Layout className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-muted-foreground">布局</span>
                <span className="capitalize">{slide.layout_hint || '通用'}</span>
              </div>

              {/* Tags */}
              <div className="flex items-start gap-2 text-sm">
                <Hash className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                <span className="text-muted-foreground">标签</span>
                <div className="flex flex-wrap gap-1">
                  {slide.tags.length > 0 ? slide.tags.map((tag, i) => (
                    <span
                      key={i}
                      className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full"
                    >
                      {tag}
                    </span>
                  )) : (
                    <span className="text-[10px] text-muted-foreground/50">无标签</span>
                  )}
                </div>
              </div>

              {/* Full text content */}
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  文本内容
                </h4>
                <div className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap max-h-80 overflow-y-auto bg-muted/10 rounded-lg p-3 border border-border/20">
                  {slide.text_summary || '(无文本内容)'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
