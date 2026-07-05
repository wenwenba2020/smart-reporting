import { useState } from 'react'
import { X, User, LogOut } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { switchAccount, logout } from '@/api/client'

export function AccountModal() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [switching, setSwitching] = useState(false)

  const showAccountManager = useProjectStore((s) => s.showAccountManager)
  const setShowAccountManager = useProjectStore((s) => s.setShowAccountManager)
  const currentUser = useProjectStore((s) => s.currentUser)
  const setCurrentUser = useProjectStore((s) => s.setCurrentUser)
  const setLoggedIn = useProjectStore((s) => s.setLoggedIn)

  if (!showAccountManager) return null

  const onClose = () => {
    setShowAccountManager(false)
    setUsername('')
    setPassword('')
    setError('')
  }

  const handleSwitch = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const u = username.trim()
    const p = password.trim()
    if (!u || !p) {
      setError('请输入用户名和密码')
      return
    }
    setSwitching(true)
    try {
      await switchAccount(u, p)
      setCurrentUser(u)
      setLoggedIn(true)
      onClose()
    } catch {
      setError('用户名或密码错误')
    } finally {
      setSwitching(false)
    }
  }

  const handleLogout = () => {
    if (confirm('确定退出登录？')) {
      logout()
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-background rounded-xl shadow-2xl w-80 flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="h-12 border-b flex items-center px-4 shrink-0">
          <span className="font-medium">账号管理</span>
          <button
            onClick={onClose}
            className="ml-auto w-7 h-7 flex items-center justify-center rounded-md hover:bg-accent"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current user */}
        <div className="p-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <User className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-medium">{currentUser}</p>
              <p className="text-xs text-muted-foreground">当前登录</p>
            </div>
            <button
              onClick={handleLogout}
              className="ml-auto flex items-center gap-1 px-2 py-1 rounded-md hover:bg-red-50 text-muted-foreground hover:text-red-600 text-xs"
            >
              <LogOut className="w-3.5 h-3.5" />
              退出
            </button>
          </div>
        </div>

        {/* Switch account form */}
        <form onSubmit={handleSwitch} className="p-4 space-y-3">
          <p className="text-xs text-muted-foreground">切换账号：</p>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="用户名"
            className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="密码"
            className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            type="submit"
            disabled={switching}
            className="w-full rounded-md bg-primary py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {switching ? '切换中...' : '切换账号'}
          </button>
        </form>
      </div>
    </div>
  )
}