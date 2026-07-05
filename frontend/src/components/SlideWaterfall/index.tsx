import { useState } from 'react'
import { Download, Lock, CheckCircle2, AlertTriangle, FileText } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { getDownloadUrl, confirmContent } from '@/api/client'
import type { ProjectStage, SlideItem } from '@/types/events'
import { TextLayout } from './text-layouts'

const API_BASE = import.meta.env.VITE_API_BASE || ''

interface SlideCardProps {
  slide: SlideItem
  projectId: string
  selected: boolean
  version: number
  stage: ProjectStage | null
  onClick: () => void
}

function SlideCard({ slide, projectId, selected, version, stage, onClick }: SlideCardProps) {
  const { slide_id, title, layout, status, locked } = slide
  const svgUrl = `${API_BASE}/project-files/${projectId}/svg_output/slide_${slide_id}.svg?v=${version}`

  const borderCls =
    status === 'failed'
      ? 'border-red-400/50 border-dashed'
      : status === 'todo'
      ? 'border-dashed border-border/40'
      : selected
      ? 'border-primary/60 ring-2 ring-primary/20 shadow-[0_0_12px_var(--glow-color)]'
      : status === 'done'
      ? 'border-border/40'
      : 'border-primary/40 shadow-[0_0_8px_var(--glow-color)]'

  return (
    <button
      onClick={onClick}
      className={`group relative w-full rounded-xl border-2 overflow-hidden transition-all hover:shadow-[0_0_15px_var(--glow-color)] text-left bg-card ${borderCls}`}
    >
      {/* Thumbnail aspect 16:9 */}
      <div className="aspect-[16/9] bg-gradient-to-br from-muted/30 to-muted/10 relative">
        {status === 'done' ? (
          <img
            src={svgUrl}
            alt={title}
            className="w-full h-full object-contain"
            loading="lazy"
          />
        ) : stage === 'awaiting_content_review' ? (
          <TextLayout slide={slide} />
        ) : status === 'generating' ? (
          <>
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin shadow-[0_0_8px_var(--glow-color)]" />
              <span className="text-[10px] text-muted-foreground">设计中...</span>
            </div>
            <div className="absolute inset-0 border-2 border-primary/30 border-dashed animate-pulse pointer-events-none rounded-xl" />
          </>
        ) : status === 'failed' ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-red-500/5">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            <span className="text-[10px] text-red-600 dark:text-red-400 font-medium">生成失败</span>
            <span className="text-[9px] text-red-500/70">点击手动修改</span>
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground/20">
            <span className="text-3xl font-light">{slide_id}</span>
          </div>
        )}

        {/* Status badges */}
        {status === 'done' && (
          <CheckCircle2 className="absolute top-1.5 right-1.5 w-4 h-4 text-green-500 drop-shadow-sm" />
        )}
        {status === 'failed' && (
          <AlertTriangle className="absolute top-1.5 right-1.5 w-4 h-4 text-red-500 drop-shadow-sm" />
        )}
        {locked && (
          <Lock
            className="absolute top-1.5 left-1.5 w-3.5 h-3.5 text-yellow-600 drop-shadow-sm"
            aria-label="已锁定"
          />
        )}
      </div>

      {/* Metadata footer */}
      <div className="px-2.5 py-2 border-t border-border/30 bg-gradient-to-r from-card to-transparent">
        <div className="flex items-center justify-between gap-1">
          <span className="text-[10px] font-mono text-primary/60 shrink-0 font-semibold">#{slide_id}</span>
          <span className="text-[9px] text-muted-foreground/60 truncate">{layout}</span>
        </div>
        <p className="text-xs font-medium truncate mt-0.5" title={title}>
          {title || <span className="text-muted-foreground italic">未命名</span>}
        </p>
      </div>
    </button>
  )
}

function ReviewBar({ projectId, totalSlides }: { projectId: string; totalSlides: number }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    setLoading(true)
    setError(null)
    try {
      await confirmContent(projectId)
      // stage_change SSE will flip the UI; no manual setState needed
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      const detail = err.response?.data?.detail || err.message || '确认失败'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <FileText className="w-3.5 h-3.5 text-primary" />
        <span>文案审核中 · 点击任一页可编辑</span>
      </div>
      <button
        onClick={handleConfirm}
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 rounded-xl p-2.5 text-sm font-medium bg-primary text-primary-foreground hover:shadow-[0_0_15px_var(--glow-color)] disabled:opacity-60 disabled:cursor-wait transition-all"
      >
        {loading ? '提交中...' : `✅ 确认文案，进入设计阶段（${totalSlides} 页）`}
      </button>
      {error && <p className="text-[11px] text-red-600 dark:text-red-400">{error}</p>}
    </>
  )
}

export function SlideWaterfall() {
  const slides = useProjectStore((s) => s.slides)
  const selectedSlideId = useProjectStore((s) => s.selectedSlideId)
  const selectSlide = useProjectStore((s) => s.selectSlide)
  const currentProject = useProjectStore((s) => s.currentProject)
  const slideVersions = useProjectStore((s) => s.slideVersions)
  const stage = useProjectStore((s) => s.stage)

  if (!currentProject) return null

  const total = slides.length
  const doneCount = slides.filter((s) => s.status === 'done').length
  const failedCount = slides.filter((s) => s.status === 'failed').length
  const settled = doneCount + failedCount
  const allSettled = total > 0 && settled === total
  const hasFailed = failedCount > 0
  const downloadUrl = getDownloadUrl(currentProject.id)

  return (
    <div className="flex flex-col h-full">
      {/* Sticky header: download + progress */}
      <div className="sticky top-0 z-10 bg-gradient-to-b from-card via-card/80 to-transparent border-b border-border/30 p-3 space-y-2 shrink-0 backdrop-blur-sm">
        {stage === 'awaiting_content_review' ? (
          <ReviewBar projectId={currentProject.id} totalSlides={total} />
        ) : allSettled ? (
          <a
            href={downloadUrl}
            target="_blank"
            rel="noreferrer"
            className={`flex items-center justify-center gap-2 rounded-xl p-2.5 text-sm font-medium transition-all ${
              hasFailed
                ? 'bg-amber-500 text-white hover:bg-amber-600 hover:shadow-[0_0_15px_rgba(245,158,11,0.4)]'
                : 'bg-primary text-primary-foreground hover:shadow-[0_0_15px_var(--glow-color)]'
            }`}
            title={hasFailed ? `${failedCount} 页生成失败，可点击失败页手动修改后再下载` : undefined}
          >
            <Download className="w-4 h-4" />
            {hasFailed ? `下载 PPTX（${failedCount} 页缺失）` : '下载 PPTX'}
          </a>
        ) : (
          <div className="flex items-center justify-center gap-2 rounded-xl p-2.5 text-sm font-medium bg-muted/50 text-muted-foreground border border-border/30">
            <Download className="w-4 h-4" />
            {total === 0 ? '等待规划' : `生成中 ${doneCount}/${total}`}
          </div>
        )}

        {total > 0 && !allSettled && stage !== 'awaiting_content_review' && (
          <div className="w-full bg-muted/50 rounded-full h-1.5 overflow-hidden border border-border/20">
            <div
              className="h-full bg-gradient-to-r from-primary/70 to-primary transition-all duration-500 shadow-[0_0_6px_var(--glow-color)]"
              style={{ width: `${(settled / total) * 100}%` }}
            />
          </div>
        )}
        {allSettled && hasFailed && (
          <p className="text-[11px] text-amber-600 dark:text-amber-400 leading-tight">
            ⚠️ {failedCount} 页生成失败 · 点击页面用 AI 对话重新修改
          </p>
        )}
      </div>

      {/* Waterfall body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {slides.length === 0 ? (
          <div className="text-center py-8 text-sm text-muted-foreground">
            完成规划后幻灯片将在此显示
          </div>
        ) : (
          slides.map((slide) => (
            <SlideCard
              key={slide.slide_id}
              slide={slide}
              projectId={currentProject.id}
              selected={selectedSlideId === slide.slide_id}
              version={slideVersions[slide.slide_id] || 0}
              stage={stage}
              onClick={() => selectSlide(slide.slide_id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
