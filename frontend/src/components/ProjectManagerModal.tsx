import { useEffect, useState } from 'react'
import { X, Trash2 } from 'lucide-react'
import { listProjects, createProject, deleteProject } from '@/api/client'
import { useProjectStore } from '@/stores/projectStore'
import type { Project } from '@/types/events'

export function ProjectManagerModal() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const showProjectManager = useProjectStore((s) => s.showProjectManager)
  const setShowProjectManager = useProjectStore((s) => s.setShowProjectManager)
  const currentProject = useProjectStore((s) => s.currentProject)
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)

  const load = async () => {
    setLoading(true)
    try {
      const list = await listProjects()
      setProjects(list)
    } catch {
      // 401 will be caught by axios interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (showProjectManager) load()
  }, [showProjectManager])

  const onClose = () => setShowProjectManager(false)

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    setCreating(true)
    try {
      const project = await createProject(name)
      setCurrentProject(project)
      useProjectStore.getState().setStage(project.stage ?? null)
      setNewName('')
      onClose()
    } catch {
      // error handled by interceptor
    } finally {
      setCreating(false)
    }
  }

  const handleSelect = (p: Project) => {
    setCurrentProject(p)
    useProjectStore.getState().setStage(p.stage ?? null)
    useProjectStore.getState().setSlides([])  // Clear old slides, loadInitialSlides will populate
    useProjectStore.getState().clearMessages()  // Clear old chat history
    onClose()
  }

  const handleDelete = async (e: React.MouseEvent, project: Project) => {
    e.stopPropagation()
    if (!confirm(`确定删除项目 "${project.name}"？\n\n此操作会永久删除 OUTLINE、SVG、历史版本等所有数据，无法恢复。`)) return
    setDeletingId(project.id)
    try {
      await deleteProject(project.id)
      setProjects((ps) => ps.filter((p) => p.id !== project.id))
      if (currentProject?.id === project.id) {
        setCurrentProject(null)
      }
    } catch {
      // 401 handled by interceptor; other errors: keep row visible
    } finally {
      setDeletingId(null)
    }
  }

  if (!showProjectManager) return null

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-background rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="h-12 border-b flex items-center px-4 shrink-0">
          <span className="font-medium">项目管理</span>
          <button
            onClick={onClose}
            className="ml-auto w-7 h-7 flex items-center justify-center rounded-md hover:bg-accent"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Create new */}
          <div className="flex gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              placeholder="新项目名称..."
              className="flex-1 rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              onClick={handleCreate}
              disabled={!newName.trim() || creating}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {creating ? '...' : '创建'}
            </button>
          </div>

          {/* Existing projects */}
          {loading ? (
            <p className="text-sm text-muted-foreground text-center py-4">加载中...</p>
          ) : projects.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              还没有项目，创建一个开始吧
            </p>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">已有项目：</p>
              {projects.map((p) => (
                <div
                  key={p.id}
                  className={`group relative w-full rounded-lg border text-left text-sm hover:bg-accent transition-colors ${
                    currentProject?.id === p.id ? 'ring-2 ring-primary' : ''
                  }`}
                >
                  <button
                    onClick={() => handleSelect(p)}
                    disabled={deletingId === p.id}
                    className="w-full p-3 text-left disabled:opacity-50"
                  >
                    <div className="flex items-center justify-between pr-8">
                      <span className="font-medium truncate">{p.name}</span>
                      <span className="text-xs text-muted-foreground shrink-0">{p.status}</span>
                    </div>
                    {p.total_slides > 0 && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {p.total_slides} 页幻灯片
                      </p>
                    )}
                  </button>
                  <button
                    onClick={(e) => handleDelete(e, p)}
                    disabled={deletingId === p.id}
                    className="absolute top-1/2 -translate-y-1/2 right-2 p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-50 text-muted-foreground hover:text-red-600 transition-opacity disabled:opacity-30"
                    title="删除项目（不可恢复）"
                    aria-label={`删除 ${p.name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
