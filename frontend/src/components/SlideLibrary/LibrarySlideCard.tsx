import { useState } from 'react'
import { Plus, Check, Square, CheckSquare } from 'lucide-react'
import type { LibrarySlide } from '@/types/events'
import { TagEditor } from './TagEditor'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'

interface Props {
  slide: LibrarySlide
  onImport?: (slideId: string) => void
  onPreview?: (slide: LibrarySlide) => void
}

export function LibrarySlideCard({ slide, onImport, onPreview }: Props) {
  const patchSlide = useSlideLibraryStore((s) => s.patchSlide)
  const selectionMode = useSlideLibraryStore((s) => s.selectionMode)
  const selectedSlideIds = useSlideLibraryStore((s) => s.selectedSlideIds)
  const toggleSelect = useSlideLibraryStore((s) => s.toggleSelect)

  const isSelected = selectedSlideIds.includes(slide.id)

  const [imported, setImported] = useState(false)
  const [localNumber, setLocalNumber] = useState(slide.slide_number || '')

  const handleNumberBlur = () => {
    if (localNumber !== (slide.slide_number || '')) {
      patchSlide(slide.id, { slide_number: localNumber || null })
    }
  }

  const handleTagsChange = (tags: string[]) => {
    patchSlide(slide.id, { tags })
  }

  const handleImport = () => {
    if (imported) return
    onImport?.(slide.id)
    setImported(true)
    setTimeout(() => setImported(false), 2000)
  }

  const handleCardClick = () => {
    if (selectionMode) {
      toggleSelect(slide.id)
    }
  }

  const handleThumbnailClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (selectionMode) {
      toggleSelect(slide.id)
    } else {
      onPreview?.(slide)
    }
  }

  return (
    <div
      onClick={handleCardClick}
      className={
        'group flex gap-2 p-2 rounded-lg transition-all border ' +
        (selectionMode ? 'cursor-pointer ' : '') +
        (isSelected
          ? 'bg-primary/5 border-primary/30'
          : 'hover:bg-accent/30 border-transparent hover:border-border/30')
      }
    >
      {/* Checkbox (selection mode only) */}
      {selectionMode && (
        <div className="shrink-0 self-center">
          {isSelected ? (
            <CheckSquare className="w-5 h-5 text-primary" />
          ) : (
            <Square className="w-5 h-5 text-muted-foreground/50" />
          )}
        </div>
      )}

      {/* Thumbnail */}
      <div
        onClick={handleThumbnailClick}
        className="w-28 h-[63px] shrink-0 bg-muted/30 rounded-md overflow-hidden border border-border/20 cursor-pointer hover:ring-2 hover:ring-primary/30 transition-all"
      >
        {slide.thumbnail_url ? (
          <img
            src={slide.thumbnail_url}
            alt={slide.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[10px] text-muted-foreground">
            {slide.slide_index}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div className="flex items-center gap-1.5">
          <input
            value={localNumber}
            onChange={(e) => setLocalNumber(e.target.value)}
            onBlur={handleNumberBlur}
            placeholder={`#${slide.slide_index}`}
            className="text-[10px] font-mono bg-transparent border-b border-transparent hover:border-border/30 focus:border-primary/30 outline-none w-12 text-muted-foreground"
          />
          <p className="text-xs font-medium truncate flex-1">{slide.title}</p>
        </div>

        <TagEditor tags={slide.tags} onTagsChange={handleTagsChange} />

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground capitalize">{slide.layout_hint || 'slide'}</span>
          <span className="text-[10px] text-muted-foreground/50">
            {(slide.text_summary || '').slice(0, 40)}...
          </span>
        </div>
      </div>

      {/* Import button (hidden in selection mode) */}
      {!selectionMode && (
        <button
          onClick={handleImport}
          disabled={imported}
          className="shrink-0 self-center opacity-0 group-hover:opacity-100 transition-all p-1 rounded-md hover:bg-primary/10 text-primary disabled:opacity-100 disabled:text-green-500"
          title="插入到项目"
        >
          {imported ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
        </button>
      )}
    </div>
  )
}
