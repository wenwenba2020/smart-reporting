import { useEffect, useRef, useState } from 'react'
import { Upload, Check, Palette, Loader2, Sparkles } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import {
  uploadReferencePptx,
  listDesignTemplates,
  getProjectDesign,
  applyDesignTemplate,
  applyDesignToAllSlides,
} from '@/api/client'
import type { DesignTemplate } from '@/types/events'

// eslint-disable-next-line @typescript-eslint/no-unused-vars
interface Props {
  selectedTemplate?: string
  onSelect?: (templateId: string) => void
}

export function StylePanel(_props: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<string | null>(null)
  const [templates, setTemplates] = useState<DesignTemplate[]>([])
  const [appliedId, setAppliedId] = useState<string | null>(null)
  const [applying, setApplying] = useState<string | null>(null)
  const [applyingToAll, setApplyingToAll] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const currentProject = useProjectStore((s) => s.currentProject)
  const slides = useProjectStore((s) => s.slides)
  const addMessage = useProjectStore((s) => s.addMessage)

  const doneCount = slides.filter((s) => s.status === 'done' && !s.locked).length

  useEffect(() => {
    listDesignTemplates()
      .then((d) => setTemplates(d.templates))
      .catch(() => setError('加载模板列表失败'))
  }, [])

  useEffect(() => {
    if (!currentProject) return
    getProjectDesign(currentProject.id)
      .then((d) => setAppliedId(d.template_id))
      .catch(() => setAppliedId(null))
  }, [currentProject])

  const handleApply = async (templateId: string) => {
    if (!currentProject || applying) return
    setApplying(templateId)
    setError(null)
    try {
      await applyDesignTemplate(currentProject.id, templateId)
      setAppliedId(templateId)
      const name = templates.find((t) => t.id === templateId)?.name || templateId
      addMessage(
        'assistant',
        `🎨 已应用「${name}」设计模板。点"确认"或重新生成时将以此风格设计 SVG。对已生成的单页，在 Modal 的 AI 栏输入"按新模板风格重新设计这一页"可单独刷新。`
      )
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(e.response?.data?.detail || e.message || '应用失败')
    } finally {
      setApplying(null)
    }
  }

  const handleApplyToAll = async () => {
    if (!currentProject || applyingToAll || doneCount === 0) return
    const confirmed = confirm(
      `将按当前 DESIGN.md 风格重新生成全部 ${doneCount} 页 SVG。\n\n` +
      `· 文字内容保持不变（title/points/备注都不动）\n` +
      `· 只重绘视觉（布局、色彩、装饰元素）\n` +
      `· 每页原版 SVG 会备份，可通过 Modal 的"撤销"回退\n` +
      `· 预计耗时 2-5 分钟（取决于页数和 LLM 速度）\n\n继续？`
    )
    if (!confirmed) return
    setApplyingToAll(true)
    setError(null)
    try {
      await applyDesignToAllSlides(currentProject.id)
      const name = templates.find((t) => t.id === appliedId)?.name || '新风格'
      addMessage(
        'assistant',
        `🎨 开始按「${name}」批量重生成全部 ${doneCount} 页。进度会在左栏智能体状态 + 右栏缩略图实时显示。`
      )
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(e.response?.data?.detail || e.message || '触发失败')
    } finally {
      setApplyingToAll(false)
    }
  }

  const handleUploadTemplate = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !currentProject) return
    e.target.value = ''
    setUploading(true)
    setUploadResult(null)
    try {
      const result = await uploadReferencePptx(currentProject.id, file)
      setUploadResult(
        `✅ 已提取 ${result.style.fonts?.length || 0} 种字体 / ${result.style.colors?.length || 0} 种配色（未来会合并到 DESIGN.md）`
      )
    } catch {
      setUploadResult('❌ 解析失败')
    }
    setUploading(false)
  }

  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1 font-display">
          设计风格 · DESIGN.md
        </h2>
        <p className="text-[11px] text-muted-foreground">
          点击应用模板 → 下一次生成 / 单页修改即用此风格
        </p>
      </div>

      {error && (
        <p className="text-xs text-red-600 dark:text-red-400 bg-red-500/10 rounded-xl px-3 py-2 border border-red-500/20">❌ {error}</p>
      )}

      {/* Built-in templates */}
      <div className="space-y-2">
        {templates.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground p-3">
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            加载中...
          </div>
        ) : (
          templates.map((t) => {
            const isApplied = appliedId === t.id
            const isApplying = applying === t.id
            return (
              <button
                key={t.id}
                onClick={() => handleApply(t.id)}
                disabled={!currentProject || isApplied || applying !== null}
                className={`w-full rounded-xl border p-3 text-left transition-all ${
                  isApplied
                    ? 'border-primary/50 ring-2 ring-primary/10 bg-primary/5 shadow-[0_0_10px_var(--glow-color)]'
                    : 'border-border/40 hover:border-primary/30 hover:bg-accent/50'
                } disabled:cursor-not-allowed`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Palette className="w-4 h-4 text-primary shrink-0" />
                    <p className="text-sm font-medium truncate">{t.name}</p>
                    <p className="text-[10px] text-muted-foreground truncate">· {t.subtitle}</p>
                  </div>
                  {isApplied && (
                    <span className="flex items-center gap-1 text-[10px] text-primary shrink-0 font-medium">
                      <Check className="w-3.5 h-3.5" />
                      已应用
                    </span>
                  )}
                  {isApplying && (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-primary shrink-0" />
                  )}
                </div>

                {/* Color swatches */}
                <div className="flex gap-1 mt-2">
                  {t.colors.slice(0, 6).map((c, i) => (
                    <span
                      key={i}
                      title={`${c.role} ${c.hex}`}
                      className="w-5 h-5 rounded-full border border-black/5 shadow-sm"
                      style={{ backgroundColor: c.hex }}
                    />
                  ))}
                </div>

                <p className="text-[11px] text-muted-foreground mt-2 leading-snug line-clamp-2">
                  {t.description}
                </p>
              </button>
            )
          })
        )}
      </div>

      {/* Apply current DESIGN.md to all slides */}
      {appliedId && doneCount > 0 && (
        <div className="border border-primary/30 bg-gradient-to-br from-primary/5 via-accent/5 to-transparent rounded-xl p-3 space-y-2">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-primary shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">测试满意，应用到全部？</p>
              <p className="text-[11px] text-muted-foreground leading-snug mt-0.5">
                先在单页 Modal 里用 AI 栏测试新风格；满意后点下面按钮批量重绘全部 {doneCount} 页（文字不变）。
              </p>
            </div>
          </div>
          <button
            onClick={handleApplyToAll}
            disabled={applyingToAll || !currentProject}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground py-2 text-sm font-medium hover:shadow-[0_0_15px_var(--glow-color)] disabled:opacity-50 transition-all"
          >
            {applyingToAll ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                提交中...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                应用到全部 {doneCount} 页
              </>
            )}
          </button>
        </div>
      )}

      {/* Upload reference PPTX (still useful for extracting brand assets) */}
      <div className="pt-2 border-t border-border/30">
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={!currentProject || uploading}
          className="w-full rounded-xl border border-dashed border-border/50 p-3 text-left transition-all hover:bg-accent/50 hover:border-primary/30 disabled:opacity-50"
        >
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-muted-foreground" />
            <div className="min-w-0">
              <p className="text-sm font-medium">{uploading ? '正在解析...' : '上传参考 PPTX'}</p>
              <p className="text-[10px] text-muted-foreground">提取颜色/字体（即将合并到 DESIGN.md）</p>
            </div>
          </div>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pptx"
          onChange={handleUploadTemplate}
        />
        {uploadResult && (
          <p className="text-xs text-muted-foreground bg-muted/30 rounded-xl p-2 mt-2 border border-border/20">
            {uploadResult}
          </p>
        )}
      </div>
    </div>
  )
}
