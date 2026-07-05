import { useEffect, useRef, useState } from 'react'
import { Upload, Loader2, BookOpen, Plus, Trash2 } from 'lucide-react'
import { useKnowledgeStore } from '@/stores/knowledgeStore'

const CATEGORIES = [
  { key: 'product', label: '产品' },
  { key: 'customer', label: '客户' },
  { key: 'meeting', label: '会议' },
  { key: 'general', label: '通用' },
] as const

export function KnowledgePanel() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [newName, setNewName] = useState('')
  const [newCategory, setNewCategory] = useState('general')
  const [showCreate, setShowCreate] = useState(false)
  const [uploading, setUploading] = useState<string | null>(null)

  const { bases, loading, selectedKbId, loadBases, createBase, removeBase, uploadFile, selectKb } =
    useKnowledgeStore()

  useEffect(() => { loadBases() }, [loadBases])

  const handleCreate = async () => {
    if (!newName.trim()) return
    await createBase(newName.trim(), newCategory)
    setNewName('')
    setShowCreate(false)
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedKbId) return
    e.target.value = ''
    setUploading(selectedKbId)
    await uploadFile(selectedKbId, file)
    setUploading(null)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-border/30 space-y-2 shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            企业知识库
          </h2>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="p-1 rounded hover:bg-accent/30 text-muted-foreground hover:text-primary"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        {showCreate && (
          <div className="space-y-1.5 p-2 rounded-lg bg-accent/10 border border-border/20">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="知识库名称"
              className="w-full text-xs px-2 py-1 rounded border border-border/30 bg-background outline-none focus:border-primary/30"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <select
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="w-full text-xs px-2 py-1 rounded border border-border/30 bg-background outline-none"
            >
              {CATEGORIES.map((c) => (
                <option key={c.key} value={c.key}>{c.label}</option>
              ))}
            </select>
            <button
              onClick={handleCreate}
              className="w-full text-xs py-1 rounded bg-primary text-primary-foreground hover:opacity-90"
            >
              创建
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
        ) : bases.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-muted-foreground gap-2">
            <BookOpen className="w-10 h-10 opacity-30" />
            <p className="text-xs">暂无知识库</p>
            <p className="text-[10px] opacity-50">上传产品文档/客户资料/会议纪要</p>
          </div>
        ) : (
          bases.map((kb) => (
            <div
              key={kb.id}
              onClick={() => selectKb(selectedKbId === kb.id ? null : kb.id)}
              className={`p-2 rounded-lg cursor-pointer transition-all border ${
                selectedKbId === kb.id
                  ? 'border-primary/30 bg-primary/5'
                  : 'border-transparent hover:bg-accent/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium">{kb.name}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-[10px] text-muted-foreground">
                      {CATEGORIES.find(c => c.key === kb.category)?.label || kb.category}
                    </span>
                    <span className="text-[10px] text-muted-foreground/50">
                      {kb.entry_count} 条
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); removeBase(kb.id) }}
                  className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-500"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>

              {selectedKbId === kb.id && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading === kb.id}
                  className="w-full mt-2 rounded border border-dashed border-border/40 p-1.5 text-[10px] text-muted-foreground hover:text-primary hover:border-primary/30 transition-all flex items-center justify-center gap-1"
                >
                  {uploading === kb.id ? (
                    <><Loader2 className="w-3 h-3 animate-spin" />解析中...</>
                  ) : (
                    <><Upload className="w-3 h-3" />上传文档</>
                  )}
                </button>
              )}
            </div>
          ))
        )}
      </div>

      <input ref={fileInputRef} type="file" className="hidden"
        accept=".pdf,.docx,.txt,.md,.csv" onChange={handleUpload} />
    </div>
  )
}
