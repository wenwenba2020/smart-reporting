import { useEffect, useRef, useState } from 'react'
import { Upload, Search, Loader2, Inbox, X, Sparkles, Plus } from 'lucide-react'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'
import { useProjectStore } from '@/stores/projectStore'
import { DeckCard } from './DeckCard'
import { SlidePreviewModal } from './SlidePreviewModal'
import type { LibrarySlide, RecommendedSlide } from '@/types/events'
import { getRecommendedSlides } from '@/api/client'

const MAX_FILE_SIZE = 50 * 1024 * 1024

export function SlideLibraryPanel() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [previewSlide, setPreviewSlide] = useState<LibrarySlide | null>(null)
  const [recommendations, setRecommendations] = useState<RecommendedSlide[]>([])
  const [recsExpanded, setRecsExpanded] = useState(true)
  const currentProject = useProjectStore((s) => s.currentProject)
  const addMessage = useProjectStore((s) => s.addMessage)

  const decks = useSlideLibraryStore((s) => s.decks)
  const loading = useSlideLibraryStore((s) => s.loading)
  const searchQuery = useSlideLibraryStore((s) => s.searchQuery)
  const uploadError = useSlideLibraryStore((s) => s.uploadError)
  const selectionMode = useSlideLibraryStore((s) => s.selectionMode)
  const selectedSlideIds = useSlideLibraryStore((s) => s.selectedSlideIds)
  const loadDecks = useSlideLibraryStore((s) => s.loadDecks)
  const uploadDeck = useSlideLibraryStore((s) => s.uploadDeck)
  const setSearchQuery = useSlideLibraryStore((s) => s.setSearchQuery)
  const importToProject = useSlideLibraryStore((s) => s.importToProject)
  const exitSelection = useSlideLibraryStore((s) => s.exitSelection)

  useEffect(() => {
    loadDecks()
  }, [loadDecks])

  useEffect(() => {
    if (!currentProject?.id) return
    getRecommendedSlides(currentProject.id, 5)
      .then((res) => {
        setRecommendations(res.recommendations || [])
      })
      .catch(() => {})
  }, [currentProject?.id])

  const handleRecImport = async (slideId: string) => {
    if (!currentProject?.id) return
    await importToProject(currentProject.id, [slideId])
    setRecommendations((prev) => prev.filter((r) => r.id !== slideId))
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''

    if (!file.name.endsWith('.pptx')) {
      addMessage?.('system', '企业库仅支持 .pptx 文件')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      addMessage?.('system', '文件过大（最大 50MB）')
      return
    }

    setUploading(true)
    const libraryId = await uploadDeck(file)
    setUploading(false)
    if (libraryId) {
      const sizeStr = file.size > 1024 * 1024
        ? (file.size / 1024 / 1024).toFixed(1) + 'MB'
        : (file.size / 1024).toFixed(0) + 'KB'
      addMessage?.('system', `已上传「${file.name}」到企业幻灯片库（${sizeStr}）`)
    }
  }

  const selectedCount = selectedSlideIds.length

  const handleBatchImport = async () => {
    if (!currentProject || selectedCount === 0) return
    const count = await importToProject(currentProject.id, selectedSlideIds)
    exitSelection()
    addMessage?.('system', `已从企业库导入 ${count} 页到当前项目`)
  }

  const safeDecks = Array.isArray(decks) ? decks : []
  const filtered = safeDecks.filter((d) =>
    !searchQuery || d.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-border/30 space-y-2 shrink-0">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest font-display">
          企业幻灯片库
        </h2>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索标题或标签..."
            className="w-full pl-7 pr-3 py-1.5 text-xs rounded-lg border border-border/30 bg-muted/20 outline-none focus:border-primary/30 transition-colors"
          />
        </div>

        {/* Selection mode bar */}
        {selectionMode && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-primary/5 border border-primary/20">
            <span className="text-xs font-medium flex-1">已选 {selectedCount} 页</span>
            <button
              onClick={exitSelection}
              className="text-xs px-2 py-1 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground flex items-center gap-1"
            >
              <X className="w-3 h-3" />
              取消
            </button>
            <button
              onClick={handleBatchImport}
              disabled={selectedCount === 0 || !currentProject}
              className="text-xs px-3 py-1 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              导入 {selectedCount} 页
            </button>
          </div>
        )}

        {/* Upload button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="w-full rounded-lg border border-dashed border-border/40 p-2 text-xs text-muted-foreground hover:text-primary hover:border-primary/30 hover:bg-accent/20 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {uploading ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              正在提取...
            </>
          ) : (
            <>
              <Upload className="w-3.5 h-3.5" />
              上传 PPT 到企业库
            </>
          )}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pptx"
          onChange={handleUpload}
        />

        {uploadError && (
          <p className="text-[10px] text-red-500">{uploadError}</p>
        )}
      </div>

      {/* Smart Recommendations */}
      {!selectionMode && recommendations.length > 0 && (
        <div className="px-3 pb-2 shrink-0">
          <button
            onClick={() => setRecsExpanded(!recsExpanded)}
            className="flex items-center gap-1.5 text-[10px] font-semibold text-primary/80 uppercase tracking-wider mb-1.5 hover:text-primary transition-colors"
          >
            <Sparkles className="w-3 h-3" />
            为你推荐
            <span className="text-[10px] text-muted-foreground normal-case ml-auto">
              {recommendations.length}
            </span>
          </button>
          {recsExpanded && (
            <div className="space-y-1">
              {recommendations.slice(0, 5).map((rec) => (
                <div
                  key={rec.id}
                  className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-accent/20 transition-colors group border border-border/10"
                >
                  <div className="w-16 h-9 shrink-0 bg-muted/20 rounded overflow-hidden border border-border/10">
                    {rec.thumbnail_url ? (
                      <img src={rec.thumbnail_url} alt={rec.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[8px] text-muted-foreground">
                        {rec.slide_index}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-medium truncate">{rec.title}</p>
                    <p className="text-[9px] text-muted-foreground">
                      {rec.layout_hint} · 匹配 {(rec.score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <button
                    onClick={() => handleRecImport(rec.id)}
                    className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-primary/10 text-primary transition-all"
                    title="导入"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Deck list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
            <Inbox className="w-10 h-10 opacity-30" />
            <p className="text-xs">
              {searchQuery ? '没有匹配的 PPT' : '上传你的第一个企业 PPT'}
            </p>
            <p className="text-[10px] opacity-50">
              上传后自动逐页提取，可编号、打标签、复用
            </p>
          </div>
        ) : (
          filtered.map((deck) => (
            <DeckCard
              key={deck.id}
              deck={deck}
              projectId={currentProject?.id ?? null}
              onPreview={setPreviewSlide}
            />
          ))
        )}
      </div>

      {/* Preview Modal */}
      {previewSlide && (
        <SlidePreviewModal
          slide={previewSlide}
          onClose={() => setPreviewSlide(null)}
        />
      )}
    </div>
  )
}
