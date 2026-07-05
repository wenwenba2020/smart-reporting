import { useEffect, useMemo, useRef, useState } from 'react'
import {
  X, ZoomIn, ZoomOut, Maximize2, RotateCw, Send, Undo2,
  FileText, ChevronDown, ChevronUp, ExternalLink,
  MessageSquare, Type, Save, PencilLine,
} from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import {
  reviseSlide, getSlideHistory, revertSlide,
  getSlideTexts, editSlideTexts,
  updateSlideContent,
  type SlideTextNode,
  type SlideContentPatch,
} from '@/api/client'
import { TextLayout } from '@/components/SlideWaterfall/text-layouts'
import type { PointItem } from '@/types/events'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const ZOOM_STEP = 0.25
const ZOOM_MIN = 0.25
const ZOOM_MAX = 5

type ZoomMode = 'fit' | 'custom'

interface MiniMsg {
  id: number
  role: 'user' | 'assistant'
  content: string
}

let _miniMsgId = 0

function ZoomToolbar({
  zoom, mode, onZoom, onFit, onReset,
}: {
  zoom: number
  mode: ZoomMode
  onZoom: (delta: number) => void
  onFit: () => void
  onReset: () => void
}) {
  const pct = Math.round(zoom * 100)
  return (
    <div className="flex items-center gap-1 text-xs">
      <button
        onClick={() => onZoom(-ZOOM_STEP)}
        disabled={zoom <= ZOOM_MIN}
        className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-accent disabled:opacity-30 transition-all"
        title="缩小"
      >
        <ZoomOut className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={onFit}
        className={`px-2 h-7 rounded-lg transition-all ${mode === 'fit' ? 'bg-primary/15 text-primary shadow-[0_0_6px_var(--glow-color)]' : 'hover:bg-accent'}`}
        title="适应窗口"
      >
        <Maximize2 className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={onReset}
        className="px-2 h-7 rounded-lg hover:bg-accent transition-all"
        title="重置为 100%"
      >
        100%
      </button>
      <button
        onClick={() => onZoom(ZOOM_STEP)}
        disabled={zoom >= ZOOM_MAX}
        className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-accent disabled:opacity-30 transition-all"
        title="放大"
      >
        <ZoomIn className="w-3.5 h-3.5" />
      </button>
      <span className="min-w-[48px] text-center text-muted-foreground tabular-nums">
        {mode === 'fit' ? '适应' : `${pct}%`}
      </span>
    </div>
  )
}

interface ContentEditorPanelProps {
  draft: { title: string; subtitle: string; points: PointItem[]; notes_speaker: string } | null
  setDraft: (d: { title: string; subtitle: string; points: PointItem[]; notes_speaker: string } | null) => void
  onSave: () => void
  saving: boolean
  error: string | null
}

function ContentEditorPanel({ draft, setDraft, onSave, saving, error }: ContentEditorPanelProps) {
  if (!draft) {
    return <div className="p-4 text-xs text-muted-foreground">加载中...</div>
  }

  const updatePointHeading = (i: number, v: string) => {
    const next = [...draft.points]
    next[i] = { ...next[i], heading: v }
    setDraft({ ...draft, points: next })
  }
  const updatePointBody = (i: number, v: string) => {
    const next = [...draft.points]
    next[i] = { ...next[i], body: v }
    setDraft({ ...draft, points: next })
  }
  const addPoint = () => setDraft({ ...draft, points: [...draft.points, { heading: '', body: null }] })
  const removePoint = (i: number) =>
    setDraft({ ...draft, points: draft.points.filter((_, idx) => idx !== i) })

  return (
    <>
      <div className="h-10 border-b flex items-center px-3 shrink-0 gap-2 text-xs font-medium">
        <PencilLine className="w-3.5 h-3.5 text-blue-500" />
        <span>内容编辑</span>
        <span className="ml-auto text-[10px] text-muted-foreground">审核态 · 不跑设计师</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="space-y-1">
          <label className="text-[10px] text-muted-foreground font-medium">标题</label>
          <input
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            disabled={saving}
            className="w-full rounded-md border px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
        </div>

        <div className="space-y-1">
          <label className="text-[10px] text-muted-foreground font-medium">副标题（可选）</label>
          <input
            value={draft.subtitle}
            onChange={(e) => setDraft({ ...draft, subtitle: e.target.value })}
            disabled={saving}
            className="w-full rounded-md border px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-[10px] text-muted-foreground font-medium">要点</label>
            <button
              type="button"
              onClick={addPoint}
              disabled={saving}
              className="text-[10px] text-primary hover:underline disabled:opacity-50"
            >
              + 添加
            </button>
          </div>
          {draft.points.length === 0 && (
            <p className="text-[10px] text-muted-foreground italic">暂无要点</p>
          )}
          {draft.points.map((p, i) => (
            <div key={i} className="rounded border border-slate-200 p-2 space-y-1.5 bg-slate-50/60">
              <div className="flex gap-1 items-start">
                <input
                  value={p.heading}
                  onChange={(e) => updatePointHeading(i, e.target.value)}
                  disabled={saving}
                  placeholder="小标题"
                  className="flex-1 rounded-md border px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => removePoint(i)}
                  disabled={saving}
                  className="w-6 h-6 flex items-center justify-center rounded-md text-muted-foreground hover:text-red-600 hover:bg-red-50 disabled:opacity-30 shrink-0"
                  title="删除"
                >
                  ×
                </button>
              </div>
              <textarea
                value={p.body ?? ''}
                onChange={(e) => updatePointBody(i, e.target.value)}
                disabled={saving}
                rows={3}
                placeholder="段落正文（可选，120-250 字）"
                className="w-full rounded-md border px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 resize-none"
              />
            </div>
          ))}
        </div>

        <div className="space-y-1">
          <label className="text-[10px] text-muted-foreground font-medium">演讲者备注</label>
          <textarea
            value={draft.notes_speaker}
            onChange={(e) => setDraft({ ...draft, notes_speaker: e.target.value })}
            disabled={saving}
            rows={3}
            className="w-full rounded-md border px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 resize-none"
          />
        </div>
      </div>

      <div className="p-2 border-t shrink-0 space-y-1.5">
        <button
          onClick={onSave}
          disabled={saving}
          className="w-full flex items-center justify-center gap-1.5 rounded-md bg-primary py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存内容'}
        </button>
        {error && <p className="text-[10px] text-red-600">{error}</p>}
      </div>
    </>
  )
}

export function SlideModal() {
  const selectedSlideId = useProjectStore((s) => s.selectedSlideId)
  const selectSlide = useProjectStore((s) => s.selectSlide)
  const currentProject = useProjectStore((s) => s.currentProject)
  const slides = useProjectStore((s) => s.slides)
  const stage = useProjectStore((s) => s.stage)
  const isReviewStage = stage === 'awaiting_content_review'

  const [svgContent, setSvgContent] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [zoomMode, setZoomMode] = useState<ZoomMode>('fit')
  const [notesExpanded, setNotesExpanded] = useState(false)
  const [miniMessages, setMiniMessages] = useState<MiniMsg[]>([])
  const [miniInput, setMiniInput] = useState('')
  const [revising, setRevising] = useState(false)
  const [historyCount, setHistoryCount] = useState(0)
  const [reverting, setReverting] = useState(false)
  const [sidebarTab, setSidebarTab] = useState<'ai' | 'text'>('ai')
  const [textNodes, setTextNodes] = useState<SlideTextNode[]>([])
  const [textEdits, setTextEdits] = useState<Record<number, string>>({})
  const [savingTexts, setSavingTexts] = useState(false)
  const [contentDraft, setContentDraft] = useState<{ title: string; subtitle: string; points: PointItem[]; notes_speaker: string } | null>(null)
  const [savingContent, setSavingContent] = useState(false)
  const [contentError, setContentError] = useState<string | null>(null)
  const miniEndRef = useRef<HTMLDivElement>(null)

  const isOpen = !!selectedSlideId && !!currentProject
  const slide = useMemo(
    () => (selectedSlideId ? slides.find((s) => s.slide_id === selectedSlideId) : null),
    [selectedSlideId, slides]
  )
  const slideStatus = slide?.status

  const onClose = () => {
    selectSlide(null)
    setSvgContent(null)
    setLoadError(null)
    setZoom(1)
    setZoomMode('fit')
    setMiniMessages([])
    setMiniInput('')
    setNotesExpanded(false)
    setHistoryCount(0)
    setSidebarTab('ai')
    setTextNodes([])
    setTextEdits({})
  }

  // Refresh history count
  const refreshHistory = async () => {
    if (!currentProject || !selectedSlideId) return
    try {
      const data = await getSlideHistory(currentProject.id, selectedSlideId)
      setHistoryCount(data.history.length)
    } catch {
      setHistoryCount(0)
    }
  }

  // Load text nodes when Text tab active or slide settles
  const refreshTextNodes = async () => {
    if (!currentProject || !selectedSlideId) return
    try {
      const data = await getSlideTexts(currentProject.id, selectedSlideId)
      setTextNodes(data.texts)
      setTextEdits({})
    } catch {
      setTextNodes([])
    }
  }

  // Load SVG when slide or status changes.
  // Status flips done→generating→done during revision — re-fetch each time
  // with cache-bust to pick up the new SVG produced by the designer.
  useEffect(() => {
    if (!isOpen || !selectedSlideId || !currentProject) return
    if (slideStatus !== 'done') {
      // While generating, keep previous SVG visible and don't overwrite with error
      return
    }
    const url = `${API_BASE}/project-files/${currentProject.id}/svg_output/slide_${selectedSlideId}.svg?t=${Date.now()}`
    setLoadError(null)
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.text()
      })
      .then(setSvgContent)
      .catch((e) => setLoadError(`SVG 未生成或加载失败：${e.message}`))
    // Also refresh history count + text nodes whenever the slide settles to 'done'
    refreshHistory()
    refreshTextNodes()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, selectedSlideId, currentProject, slideStatus])

  // Lock body scroll + ESC to close
  useEffect(() => {
    if (!isOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      window.removeEventListener('keydown', onKey)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  // Scroll mini chat to bottom
  useEffect(() => {
    miniEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [miniMessages])

  // Initialize content draft when in review stage or slide changes
  useEffect(() => {
    if (!slide) {
      setContentDraft(null)
      return
    }
    if (isReviewStage) {
      setContentDraft({
        title: slide.title || '',
        subtitle: '',
        points: (slide.points || []).map((p) => ({ heading: p.heading, body: p.body ?? null })),
        notes_speaker: slide.notes_speaker || '',
      })
      setContentError(null)
    }
  }, [slide, isReviewStage])

  if (!isOpen || !slide) return null

  const handleZoom = (delta: number) => {
    setZoom((z) => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Number((z + delta).toFixed(2)))))
    setZoomMode('custom')
  }
  const handleFit = () => { setZoom(1); setZoomMode('fit') }
  const handleReset = () => { setZoom(1); setZoomMode('custom') }

  const handleMiniSend = async () => {
    const text = miniInput.trim()
    if (!text || !currentProject || !selectedSlideId || revising) return
    setMiniInput('')
    setMiniMessages((m) => [...m, { id: ++_miniMsgId, role: 'user', content: text }])
    setRevising(true)
    try {
      await reviseSlide(currentProject.id, selectedSlideId, text)
      setMiniMessages((m) => [
        ...m,
        {
          id: ++_miniMsgId,
          role: 'assistant',
          content: '✓ 设计师已接到指令，重新生成这一页。完成后画面会自动刷新。',
        },
      ])
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      const detail = e.response?.data?.detail || e.message || '请求失败'
      setMiniMessages((m) => [
        ...m,
        { id: ++_miniMsgId, role: 'assistant', content: `❌ ${detail}` },
      ])
    } finally {
      setRevising(false)
    }
  }

  const handleSaveTexts = async () => {
    if (!currentProject || !selectedSlideId || savingTexts) return
    const edits = Object.entries(textEdits)
      .filter(([i, v]) => {
        const orig = textNodes.find((n) => n.index === Number(i))?.text
        return orig !== undefined && v !== orig
      })
      .map(([i, new_text]) => ({ index: Number(i), new_text }))
    if (!edits.length) return
    setSavingTexts(true)
    try {
      await editSlideTexts(currentProject.id, selectedSlideId, edits)
      setTextEdits({})
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      alert('保存失败：' + (e.response?.data?.detail || e.message || '未知错误'))
    } finally {
      setSavingTexts(false)
    }
  }

  const handleRevert = async () => {
    if (!currentProject || !selectedSlideId || reverting || historyCount === 0) return
    if (!confirm('撤销将恢复到上一个版本，当前改动会丢失。继续？')) return
    setReverting(true)
    try {
      await revertSlide(currentProject.id, selectedSlideId)
      setMiniMessages((m) => [
        ...m,
        {
          id: ++_miniMsgId,
          role: 'assistant',
          content: '↩ 已恢复上一版本，正在重新打包 PPTX...',
        },
      ])
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      const detail = e.response?.data?.detail || e.message || '撤销失败'
      setMiniMessages((m) => [
        ...m,
        { id: ++_miniMsgId, role: 'assistant', content: `❌ ${detail}` },
      ])
    } finally {
      setReverting(false)
    }
  }

  const handleSaveContent = async () => {
    if (!currentProject || !selectedSlideId || !contentDraft || savingContent) return
    setSavingContent(true)
    setContentError(null)
    try {
      const patch: SlideContentPatch = {
        title: contentDraft.title,
        points: contentDraft.points
          .filter((p) => p.heading.trim() !== '' || (p.body && p.body.trim() !== ''))
          .map((p) => ({
            heading: p.heading.trim(),
            body: p.body && p.body.trim() !== '' ? p.body : null,
          })),
        notes_speaker: contentDraft.notes_speaker,
      }
      if (contentDraft.subtitle.trim()) {
        patch.subtitle = contentDraft.subtitle
      }
      await updateSlideContent(currentProject.id, selectedSlideId, patch)
      // Backend emits slide_content_changed SSE → store re-loads; no manual refresh needed.
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setContentError(e.response?.data?.detail || e.message || '保存失败')
    } finally {
      setSavingContent(false)
    }
  }

  const notes = slide.notes_speaker?.trim() || ''
  const downloadHref = `${API_BASE}/project-files/${currentProject!.id}/svg_output/slide_${slide.slide_id}.svg`

  // Determine SVG container style based on zoom mode
  // fit: width 100% + aspect-ratio 自动算高度，maxHeight 约束后反向缩宽实现 contain
  const svgWrapperStyle: React.CSSProperties =
    zoomMode === 'fit'
      ? {
          width: '100%',
          maxWidth: 'calc((100vh - 180px) * 16 / 9)',
          aspectRatio: '16/9',
          maxHeight: '100%',
        }
      : { width: `${960 * zoom}px`, height: `${540 * zoom}px`, flexShrink: 0 }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-background/95 rounded-2xl shadow-2xl border border-border/30 w-[96%] h-[94%] max-w-[1600px] flex flex-col overflow-hidden backdrop-blur-sm"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="h-12 border-b border-border/30 flex items-center px-3 gap-3 shrink-0 bg-gradient-to-r from-card/50 to-transparent">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs font-mono text-primary/70 shrink-0 font-semibold">#{slide.slide_id}</span>
            <span className="text-sm font-medium truncate">{slide.title || '未命名'}</span>
            <span className="text-[10px] text-muted-foreground shrink-0">· {slide.layout}</span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={handleRevert}
              disabled={historyCount === 0 || reverting || revising}
              className="flex items-center gap-1 h-7 px-2 rounded-lg hover:bg-accent text-xs disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              title={
                historyCount === 0
                  ? '没有可撤销的历史版本'
                  : `撤销到上一版本（还剩 ${historyCount} 个可撤销）`
              }
            >
              <Undo2 className="w-3.5 h-3.5" />
              撤销
              {historyCount > 0 && (
                <span className="text-[10px] text-muted-foreground">({historyCount})</span>
              )}
            </button>
            <div className="w-px h-5 bg-border/50" />
            <ZoomToolbar
              zoom={zoom}
              mode={zoomMode}
              onZoom={handleZoom}
              onFit={handleFit}
              onReset={handleReset}
            />
            <div className="w-px h-5 bg-border/50" />
            <a
              href={downloadHref}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
              title="在新标签页打开 SVG"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              原图
            </a>
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-accent transition-all"
              title="关闭 (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Main body: SVG + AI sidebar */}
        <div className="flex-1 flex min-h-0">
          {/* SVG viewer */}
          <div className="flex-1 min-w-0 bg-muted/30 overflow-auto flex items-center justify-center p-4 relative">
            {isReviewStage ? (
              <div className="w-full max-w-3xl space-y-3">
                <div className="text-center text-xs text-muted-foreground">
                  审核态预览 · 设计稿将在确认后生成
                </div>
                <div className="relative w-full aspect-[16/9] bg-white rounded-lg shadow-xl border overflow-hidden">
                  <TextLayout slide={slide} />
                </div>
                <p className="text-center text-[11px] text-muted-foreground">
                  在右侧编辑标题 / 要点 / 演讲者备注，保存后此预览会自动刷新
                </p>
              </div>
            ) : slideStatus === 'failed' && !svgContent ? (
              <div className="text-center max-w-md space-y-3 px-4">
                <p className="text-4xl">⚠️</p>
                <p className="text-base font-semibold text-red-600">这一页生成失败</p>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  设计师两轮重试均失败。你可以在右侧 AI 对话栏输入修改指令手动重新生成，
                  或回到大纲阶段修改本页的 visual_intent 后重新生成。
                </p>
              </div>
            ) : loadError ? (
              <div className="text-center text-muted-foreground">
                <p className="text-2xl mb-2">📄</p>
                <p className="text-sm">{loadError}</p>
              </div>
            ) : !svgContent ? (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <p className="text-sm">加载幻灯片...</p>
              </div>
            ) : (
              <div
                style={svgWrapperStyle}
                className="shadow-xl rounded-lg overflow-hidden border bg-white transition-[width,height] duration-150 relative"
              >
                <div
                  dangerouslySetInnerHTML={{ __html: svgContent }}
                  style={{ width: '100%', height: '100%' }}
                  className="[&>svg]:w-full [&>svg]:h-full"
                />
                {slideStatus === 'generating' && (
                  <div className="absolute inset-0 bg-background/75 backdrop-blur-sm flex flex-col items-center justify-center gap-2">
                    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm font-medium">设计师正在重新生成...</p>
                    <p className="text-xs text-muted-foreground">完成后自动刷新</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar · AI 对话 / 手动文字编辑 / 内容编辑（审核态） */}
          <div className="w-[340px] border-l flex flex-col shrink-0 bg-background">
            {isReviewStage ? (
              <ContentEditorPanel
                draft={contentDraft}
                setDraft={setContentDraft}
                onSave={handleSaveContent}
                saving={savingContent}
                error={contentError}
              />
            ) : (
            <>
            {/* Tabs */}
            <div className="h-10 border-b border-border/30 flex shrink-0">
              <button
                onClick={() => setSidebarTab('ai')}
                className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-medium transition-all relative ${
                  sidebarTab === 'ai' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" /> AI 对话
                {sidebarTab === 'ai' && (
                  <span className="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-primary rounded-full shadow-[0_0_6px_var(--glow-color)]" />
                )}
              </button>
              <button
                onClick={() => setSidebarTab('text')}
                className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-medium transition-all relative ${
                  sidebarTab === 'text' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Type className="w-3.5 h-3.5" />
                编辑文字
                {textNodes.length > 0 && (
                  <span className="text-[10px] text-muted-foreground/70">({textNodes.length})</span>
                )}
                {sidebarTab === 'text' && (
                  <span className="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-primary rounded-full shadow-[0_0_6px_var(--glow-color)]" />
                )}
              </button>
            </div>

            {sidebarTab === 'ai' ? (
              <>
                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                  {miniMessages.length === 0 ? (
                    <div className="text-center text-xs text-muted-foreground py-6 space-y-1.5">
                      <p>例如：</p>
                      <p className="italic">"标题改得更有冲击力"</p>
                      <p className="italic">"这页太满了，精简一下"</p>
                      <p className="italic">"换成深色背景"</p>
                    </div>
                  ) : (
                    miniMessages.map((m) => (
                      <div
                        key={m.id}
                        className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[85%] rounded-xl px-3 py-2 text-xs whitespace-pre-wrap transition-all ${
                            m.role === 'user'
                              ? 'bg-primary text-primary-foreground shadow-[0_0_8px_var(--glow-color)]'
                              : 'bg-muted/50 border border-border/30'
                          }`}
                        >
                          {m.content}
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={miniEndRef} />
                </div>

                <div className="p-2 border-t border-border/30 shrink-0 space-y-1.5 bg-gradient-to-t from-card/30 to-transparent">
                  <div className="flex gap-1.5">
                    <input
                      type="text"
                      value={miniInput}
                      onChange={(e) => setMiniInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          handleMiniSend()
                        }
                      }}
                      disabled={revising}
                      placeholder={revising ? '设计师生成中...' : '修改这一页...'}
                      className="flex-1 rounded-lg border border-border/50 bg-background/50 px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 disabled:opacity-50 transition-all"
                    />
                    <button
                      onClick={handleMiniSend}
                      disabled={!miniInput.trim() || revising}
                      className="w-7 h-7 flex items-center justify-center rounded-lg bg-primary text-primary-foreground hover:shadow-[0_0_10px_var(--glow-color)] disabled:opacity-30 shrink-0 transition-all"
                    >
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                    <RotateCw className="w-3 h-3" />
                    关闭后对话归档到主时间线
                  </div>
                </div>
              </>
            ) : (
              // Manual text editing
              <>
                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                  {textNodes.length === 0 ? (
                    <div className="text-center text-xs text-muted-foreground py-6">
                      未解析到可编辑文字
                    </div>
                  ) : (
                    textNodes.map((n, displayIdx) => {
                      const edited = textEdits[n.index] ?? n.text
                      const changed = edited !== n.text
                      return (
                        <div key={n.index} className="space-y-1">
                          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                            <span className="font-mono">#{displayIdx + 1}</span>
                            <span className="uppercase">{n.tag}</span>
                            {changed && <span className="text-amber-600">· 已修改</span>}
                          </div>
                          <textarea
                            value={edited}
                            onChange={(e) =>
                              setTextEdits((m) => ({ ...m, [n.index]: e.target.value }))
                            }
                            rows={Math.max(1, Math.min(4, edited.split('\n').length))}
                            disabled={savingTexts || revising || reverting}
                            className={`w-full rounded-md border px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring resize-none ${
                              changed ? 'border-amber-400 bg-amber-50' : ''
                            }`}
                          />
                        </div>
                      )
                    })
                  )}
                </div>

                <div className="p-2 border-t border-border/30 shrink-0 space-y-1.5 bg-gradient-to-t from-card/30 to-transparent">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] text-muted-foreground">
                      {Object.keys(textEdits).filter((i) => {
                        const orig = textNodes.find((n) => n.index === Number(i))?.text
                        return orig !== undefined && textEdits[Number(i)] !== orig
                      }).length} 处修改
                    </span>
                    <button
                      onClick={handleSaveTexts}
                      disabled={savingTexts || revising || Object.keys(textEdits).length === 0}
                      className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:shadow-[0_0_10px_var(--glow-color)] disabled:opacity-30 transition-all"
                    >
                      <Save className="w-3.5 h-3.5" />
                      {savingTexts ? '保存中...' : '保存修改'}
                    </button>
                  </div>
                  <p className="text-[10px] text-muted-foreground">
                    直接改文字 · 不走 AI · 保留所有样式。可用"撤销"按钮回退。
                  </p>
                </div>
              </>
            )}
            </>
            )}
          </div>
        </div>

        {/* Notes footer */}
        <div className="border-t border-border/30 shrink-0 bg-gradient-to-t from-card/20 to-transparent">
          <button
            onClick={() => setNotesExpanded((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-2 text-xs hover:bg-accent/50 transition-colors"
          >
            <span className="flex items-center gap-2 text-muted-foreground">
              <FileText className="w-3.5 h-3.5 text-primary" />
              <span className="font-medium">演讲者备注</span>
              <span className="text-[10px] text-muted-foreground/70">
                · {notes ? `${notes.length} 字` : '文案师尚未生成'}
              </span>
            </span>
            {notesExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>
          {notesExpanded && (
            <div className="px-4 pb-3 max-h-[140px] overflow-y-auto">
              {notes ? (
                <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">
                  {notes}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground italic">
                  等文案师完成后，演讲者备注将在此显示。
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
