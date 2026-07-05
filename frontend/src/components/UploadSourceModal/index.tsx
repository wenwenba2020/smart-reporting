import { useEffect, useRef, useState } from 'react'
import { X, Upload, Link as LinkIcon, Database, FileText, Presentation, Globe } from 'lucide-react'
import { uploadDocument, uploadReferencePptx, researchUrls, type ResearchProvider } from '@/api/client'
import { useProjectStore } from '@/stores/projectStore'

type UploadResult =
  | { kind: 'source' | 'reference'; filename: string; detail: string }
  | { kind: 'url'; filename: string; detail: string; failed?: boolean }

export function UploadSourceModal({ onClose }: { onClose: () => void }) {
  const currentProject = useProjectStore((s) => s.currentProject)
  const addMessage = useProjectStore((s) => s.addMessage)
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState<UploadResult[]>([])
  const [error, setError] = useState<string | null>(null)
  const [urls, setUrls] = useState<string[]>([''])
  const [deepCrawl, setDeepCrawl] = useState(false)
  const [provider, setProvider] = useState<ResearchProvider>('exa')
  const [fetchingUrls, setFetchingUrls] = useState(false)
  const docInputRef = useRef<HTMLInputElement>(null)
  const pptxInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  const handleFetchUrls = async () => {
    if (!currentProject || fetchingUrls) return
    const cleaned = urls.map((u) => u.trim()).filter((u) => u.length > 0)
    if (cleaned.length === 0) {
      setError('请至少输入一个网址')
      return
    }
    if (deepCrawl && cleaned.length > 3) {
      setError('深度抓取单次最多 3 个 URL')
      return
    }
    setError(null)
    setFetchingUrls(true)
    try {
      const resp = await researchUrls(currentProject.id, cleaned, deepCrawl, provider)
      for (const r of resp.results) {
        if (r.status === 'ok') {
          setResults((rs) => [...rs, {
            kind: 'url',
            filename: r.title || r.url,
            detail: `已抓取 ${r.chars ?? 0} 字符 · ${(r.preview || '').slice(0, 120)}...`,
          }])
          addMessage('assistant', `🌐 已抓取网址内容：${r.title || r.url}（${r.chars ?? 0} 字符）`)
        } else {
          setResults((rs) => [...rs, {
            kind: 'url',
            filename: r.url,
            detail: `❌ 抓取失败：${r.error || '未知原因'}`,
            failed: true,
          }])
        }
      }
      setUrls([''])
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(e.response?.data?.detail || e.message || '抓取失败')
    } finally {
      setFetchingUrls(false)
    }
  }

  const handleDocFiles = async (files: FileList | null) => {
    if (!files || !currentProject) return
    setError(null)
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        const ext = file.name.toLowerCase().split('.').pop() || ''
        if (ext === 'pptx') {
          const r = await uploadReferencePptx(currentProject.id, file)
          setResults((rs) => [...rs, {
            kind: 'reference',
            filename: file.name,
            detail: `已提取 ${r.images_extracted ?? 0} 张图片 + 风格信息`,
          }])
          addMessage('assistant', `📎 参考 PPTX 已解析：${file.name}（${r.images_extracted ?? 0} 张图片）`)
        } else if (['pdf', 'docx', 'txt', 'md'].includes(ext)) {
          const r = await uploadDocument(currentProject.id, file)
          setResults((rs) => [...rs, {
            kind: 'source',
            filename: file.name,
            detail: (r.markdown_preview || '').slice(0, 120) + '...',
          }])
          addMessage('assistant', `📎 源文档已解析：${file.name}\n${(r.markdown_preview || '').slice(0, 200)}...`)
        } else {
          setError(`不支持的格式: ${ext}`)
        }
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(e.response?.data?.detail || e.message || '上传失败')
    } finally {
      setUploading(false)
      if (docInputRef.current) docInputRef.current.value = ''
      if (pptxInputRef.current) pptxInputRef.current.value = ''
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-background rounded-xl shadow-2xl w-[640px] max-w-[96vw] max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="h-12 border-b flex items-center px-4 shrink-0">
          <span className="text-sm font-semibold">添加源材料</span>
          <button onClick={onClose} className="ml-auto w-7 h-7 flex items-center justify-center rounded-md hover:bg-accent">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Section 1: Local files */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">本地文件</h3>
            </div>
            <p className="text-xs text-muted-foreground mb-2">
              PDF / Word / PPTX / TXT / MD · 单个文件 ≤ 50MB
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => docInputRef.current?.click()}
                disabled={uploading || !currentProject}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-primary/30 py-4 text-sm hover:bg-primary/5 transition-colors disabled:opacity-50"
              >
                <Upload className="w-4 h-4" />
                <span>上传源文档（PDF/Word/TXT/MD）</span>
              </button>
              <button
                onClick={() => pptxInputRef.current?.click()}
                disabled={uploading || !currentProject}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-amber-400/50 py-4 text-sm hover:bg-amber-50 transition-colors disabled:opacity-50"
              >
                <Presentation className="w-4 h-4 text-amber-600" />
                <span>上传参考 PPTX（风格/图片）</span>
              </button>
            </div>
            <input
              ref={docInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.txt,.md"
              multiple
              onChange={(e) => handleDocFiles(e.target.files)}
            />
            <input
              ref={pptxInputRef}
              type="file"
              className="hidden"
              accept=".pptx"
              multiple
              onChange={(e) => handleDocFiles(e.target.files)}
            />
          </section>

          {/* Section 2: URLs */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <LinkIcon className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">参考网站链接</h3>
            </div>
            <p className="text-xs text-muted-foreground mb-2">
              粘贴要调研的网址，将抓取页面内容作为源材料供规划师与文案师使用（单次最多 10 个）。
            </p>
            {urls.map((u, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  type="url"
                  placeholder="https://..."
                  value={u}
                  onChange={(e) => setUrls((us) => us.map((v, j) => (j === i ? e.target.value : v)))}
                  disabled={fetchingUrls}
                  className="flex-1 rounded-md border px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                />
                {urls.length > 1 && (
                  <button
                    onClick={() => setUrls((us) => us.filter((_, j) => j !== i))}
                    disabled={fetchingUrls}
                    className="px-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    移除
                  </button>
                )}
              </div>
            ))}
            <div className="flex items-center gap-4 mt-2 text-xs">
              <span className="text-muted-foreground">抓取服务：</span>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="radio"
                  name="provider"
                  value="exa"
                  checked={provider === 'exa'}
                  onChange={() => setProvider('exa')}
                  disabled={fetchingUrls}
                  className="accent-primary"
                />
                <span>Exa（默认 · 实时抓取 + 子页）</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="radio"
                  name="provider"
                  value="tavily"
                  checked={provider === 'tavily'}
                  onChange={() => setProvider('tavily')}
                  disabled={fetchingUrls}
                  className="accent-primary"
                />
                <span>Tavily（备选）</span>
              </label>
            </div>
            <label className="flex items-center gap-2 mt-2 text-xs text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={deepCrawl}
                onChange={(e) => setDeepCrawl(e.target.checked)}
                disabled={fetchingUrls}
                className="h-3.5 w-3.5 accent-primary"
              />
              <span>
                深度抓取（抓取站内多个子页，单次最多 3 个 URL · 约 30-60 秒）
              </span>
            </label>
            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={() => setUrls((us) => [...us, ''])}
                disabled={fetchingUrls || urls.length >= 10}
                className="text-xs text-primary hover:underline disabled:opacity-40"
              >
                + 添加另一个链接
              </button>
              <button
                onClick={handleFetchUrls}
                disabled={fetchingUrls || !currentProject}
                className="ml-auto flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                <Globe className="w-3.5 h-3.5" />
                {fetchingUrls ? (deepCrawl ? '深度抓取中...' : '抓取中...') : (deepCrawl ? '深度抓取' : '抓取')}
              </button>
            </div>
          </section>

          {/* Section 3: Knowledge base */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">用户知识库</h3>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">即将上线</span>
            </div>
            <p className="text-xs text-muted-foreground mb-2">
              链接已有企业/个人知识库（Notion / 飞书 / 语雀等），让规划师按需检索相关内容。
            </p>
            <button
              disabled
              className="w-full flex items-center justify-center gap-2 rounded-lg border py-3 text-sm text-muted-foreground opacity-50"
            >
              <Database className="w-4 h-4" />
              链接知识库
            </button>
          </section>

          {/* Results */}
          {(uploading || results.length > 0 || error) && (
            <section className="border-t pt-3">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                上传结果
              </h4>
              {uploading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  解析中...
                </div>
              )}
              {error && (
                <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
                  ❌ {error}
                </p>
              )}
              {results.map((r, i) => {
                const failed = r.kind === 'url' && r.failed
                const kindLabel =
                  r.kind === 'reference' ? '参考 PPTX' :
                  r.kind === 'url' ? '网页' : '源文档'
                const colorCls = failed
                  ? 'bg-red-50 border-red-200'
                  : 'bg-green-50 border-green-200'
                const textCls = failed ? 'text-red-800' : 'text-green-800'
                const bodyCls = failed ? 'text-red-700' : 'text-green-700'
                const mark = failed ? '✗' : '✓'
                const markCls = failed ? 'text-red-600' : 'text-green-600'
                return (
                  <div
                    key={i}
                    className={`flex items-start gap-2 text-xs rounded-md border px-3 py-2 mb-1.5 ${colorCls}`}
                  >
                    <span className={`${markCls} shrink-0`}>{mark}</span>
                    <div className="min-w-0">
                      <p className={`font-medium truncate ${textCls}`}>
                        {kindLabel} · {r.filename}
                      </p>
                      <p className={`${bodyCls} mt-0.5 break-words`}>{r.detail}</p>
                    </div>
                  </div>
                )
              })}
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-4 py-3 flex items-center justify-between shrink-0">
          <p className="text-xs text-muted-foreground">
            {results.length > 0 ? `已上传 ${results.length} 个文件` : '可拖拽或点击选择文件'}
          </p>
          <button
            onClick={onClose}
            className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  )
}
