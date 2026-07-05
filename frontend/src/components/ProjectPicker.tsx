import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { listProjects, createProject, deleteProject } from '@/api/client'
import { useProjectStore } from '@/stores/projectStore'
import type { Project } from '@/types/events'

export function ProjectPicker() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const { setCurrentProject } = useProjectStore()

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
    load()
  }, [])

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    setCreating(true)
    try {
      const project = await createProject(name)
      setCurrentProject(project)
      useProjectStore.getState().setStage(project.stage ?? null)
    } catch {
      // error handled by interceptor
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (e: React.MouseEvent, project: Project) => {
    e.stopPropagation()
    if (!confirm(`确定删除项目 "${project.name}"？\n\n此操作会永久删除 OUTLINE、SVG、历史版本等所有数据，无法恢复。`)) return
    setDeletingId(project.id)
    try {
      await deleteProject(project.id)
      setProjects((ps) => ps.filter((p) => p.id !== project.id))
    } catch {
      // 401 handled by interceptor; other errors: keep row visible
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        加载项目列表...
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center h-full">
      <div className="w-96 space-y-6">
        <h2 className="text-lg font-bold text-center">选择或创建项目</h2>

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
        {projects.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">已有项目：</p>
            {projects.map((p) => (
              <div
                key={p.id}
                className="group relative w-full rounded-lg border text-left text-sm hover:bg-accent transition-colors"
              >
                <button
                  onClick={() => {
                    setCurrentProject(p)
                    useProjectStore.getState().setStage(p.stage ?? null)
                  }}
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

        {projects.length === 0 && (
          <p className="text-sm text-muted-foreground text-center">
            还没有项目，创建一个开始吧
          </p>
        )}
      </div>
    </div>
  )
}
