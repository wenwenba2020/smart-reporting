import { useEffect } from 'react'
import { useProjectStore } from '@/stores/projectStore'
import { autoLogin, listProjects, createProject } from '@/api/client'
import { AppShell } from '@/components/layout/AppShell'
import { SlideModal } from '@/components/SlideModal'
import { ProjectManagerModal } from '@/components/ProjectManagerModal'
import { AccountModal } from '@/components/AccountModal'

function App() {
  const isLoggedIn = useProjectStore((s) => s.isLoggedIn)
  const setLoggedIn = useProjectStore((s) => s.setLoggedIn)
  const currentProject = useProjectStore((s) => s.currentProject)
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)
  const theme = useProjectStore((s) => s.theme)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  useEffect(() => {
    const init = async () => {
      if (!isLoggedIn) {
        try {
          await autoLogin()
          setLoggedIn(true)
        } catch {
          console.error('Auto login failed')
          return
        }
      }

      if (!currentProject) {
        try {
          const projects = await listProjects()
          if (projects.length > 0) {
            setCurrentProject(projects[0])
            useProjectStore.getState().setStage(projects[0].stage ?? null)
          } else {
            const project = await createProject('我的第一个 PPT')
            setCurrentProject(project)
            useProjectStore.getState().setStage(project.stage ?? null)
          }
        } catch (err) {
          console.error('Failed to load projects:', err)
        }
      }
    }
    init()
  }, [isLoggedIn])

  if (!isLoggedIn || !currentProject) {
    return (
      <div className="h-screen flex items-center justify-center bg-background relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-primary/20 rounded-full blur-3xl animate-glow-pulse" />
        </div>
        <div className="flex flex-col items-center gap-4 relative z-10">
          <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin shadow-[0_0_15px_var(--glow-color)]" />
          <p className="text-sm text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <AppShell />
      <SlideModal />
      <ProjectManagerModal />
      <AccountModal />
    </>
  )
}

export default App
