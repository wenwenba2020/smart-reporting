import { useState } from 'react'
import { ChevronDown, ChevronRight, Trash2, Pencil, CheckSquare, Square, Layers, Wand2 } from 'lucide-react'
import type { LibraryDeck, LibrarySlide } from '@/types/events'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'
import { extractLibraryDesign } from '@/api/client'
import { LibrarySlideCard } from './LibrarySlideCard'

interface Props {
  deck: LibraryDeck
  projectId: string | null
  onPreview?: (slide: LibrarySlide) => void
}

export function DeckCard({ deck, projectId, onPreview }: Props) {
  const [editingName, setEditingName] = useState(false)
  const [name, setName] = useState(deck.name)
  const expandedDeckId = useSlideLibraryStore((s) => s.expandedDeckId)
  const expandedSlides = useSlideLibraryStore((s) => s.expandedSlides)
  const toggleExpand = useSlideLibraryStore((s) => s.toggleExpand)
  const removeDeck = useSlideLibraryStore((s) => s.removeDeck)
  const renameDeck = useSlideLibraryStore((s) => s.renameDeck)
  const importToProject = useSlideLibraryStore((s) => s.importToProject)
  const selectionMode = useSlideLibraryStore((s) => s.selectionMode)
  const selectedSlideIds = useSlideLibraryStore((s) => s.selectedSlideIds)
  const selectAllInDeck = useSlideLibraryStore((s) => s.selectAllInDeck)
  const enterSelection = useSlideLibraryStore((s) => s.enterSelection)
  const exitSelection = useSlideLibraryStore((s) => s.exitSelection)

  const [extracting, setExtracting] = useState(false)

  const handleExtractDesign = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (extracting) return
    setExtracting(true)
    try {
      const result = await extractLibraryDesign(deck.id)
      alert(`已保存为模板「${result.name}」`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail || '提取失败')
    }
    setExtracting(false)
  }

  const isExpanded = expandedDeckId === deck.id

  const slideIds = expandedSlides.map((s) => s.id)
  const allSelected = slideIds.length > 0 && slideIds.every((id) => selectedSlideIds.includes(id))

  const handleToggle = () => {
    toggleExpand(deck.id)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm(`删除「${deck.name}」及其全部 ${deck.slide_count} 页？`)) {
      removeDeck(deck.id)
    }
  }

  const handleNameBlur = () => {
    setEditingName(false)
    const trimmed = name.trim()
    if (trimmed && trimmed !== deck.name) {
      renameDeck(deck.id, trimmed)
    } else {
      setName(deck.name)
    }
  }

  const handleImportSlide = async (slideId: string) => {
    if (!projectId) return
    await importToProject(projectId, [slideId])
  }

  const handleSelectAll = () => {
    selectAllInDeck(slideIds)
  }

  const handleToggleSelectionMode = () => {
    if (selectionMode) {
      exitSelection()
    } else {
      enterSelection()
    }
  }

  return (
    <div className="group border border-border/20 rounded-xl overflow-hidden bg-card/30 transition-all">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 hover:bg-accent/20 transition-colors">
        <button
          onClick={handleToggle}
          className="text-muted-foreground shrink-0 hover:text-foreground transition-colors"
        >
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {editingName ? (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleNameBlur}
            onKeyDown={(e) => { if (e.key === 'Enter') handleNameBlur() }}
            className="flex-1 text-sm font-medium bg-transparent border-b border-primary/30 outline-none px-1"
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="flex-1 text-sm font-medium truncate">{deck.name}</span>
        )}

        <span className="text-[10px] text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded-full">
          {deck.slide_count} 页
        </span>

        {/* Enter/exit selection mode (only when expanded) */}
        {isExpanded && (
          <button
            onClick={handleToggleSelectionMode}
            className={`p-0.5 transition-all ${
              selectionMode
                ? 'text-primary'
                : 'opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-primary'
            }`}
            title={selectionMode ? '退出选择模式' : '批量选择'}
          >
            <Layers className="w-3 h-3" />
          </button>
        )}

        {/* Extract design button */}
        {isExpanded && (
          <button
            onClick={handleExtractDesign}
            disabled={extracting}
            className={`shrink-0 p-0.5 rounded transition-all ${
              extracting ? 'text-primary animate-pulse' : 'text-muted-foreground opacity-0 group-hover:opacity-100'
            }`}
            title="提取设计为模板"
          >
            <Wand2 className="w-3.5 h-3.5" />
          </button>
        )}

        <button
          onClick={(e) => { e.stopPropagation(); setEditingName(true); setName(deck.name) }}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-primary transition-all"
          title="重命名"
        >
          <Pencil className="w-3 h-3" />
        </button>

        <button
          onClick={handleDelete}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-500 transition-all"
          title="删除"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {/* Select-all bar (only when expanded AND in selection mode) */}
      {isExpanded && selectionMode && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-t border-border/10 bg-primary/3">
          <button
            onClick={handleSelectAll}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
          >
            {allSelected ? (
              <CheckSquare className="w-4 h-4 text-primary" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            <span>{allSelected ? '取消全选' : '全选'}</span>
          </button>
        </div>
      )}

      {/* Expanded slides */}
      {isExpanded && (
        <div className="border-t border-border/10 divide-y divide-border/10">
          {expandedSlides.length === 0 ? (
            <p className="text-xs text-muted-foreground p-4 text-center">加载中...</p>
          ) : (
            expandedSlides.map((slide) => (
              <LibrarySlideCard
                key={slide.id}
                slide={slide}
                onImport={handleImportSlide}
                onPreview={onPreview}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
