import { useState } from 'react'
import { login } from '@/api/client'
import { useProjectStore } from '@/stores/projectStore'

export function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setLoggedIn = useProjectStore((s) => s.setLoggedIn)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      setLoggedIn(true)
    } catch {
      setError('用户名或密码错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <form
        onSubmit={handleSubmit}
        className="w-80 space-y-4 rounded-lg border p-6 shadow-sm"
      >
        <h1 className="text-xl font-bold text-center">PPT 智能助手</h1>
        <div>
          <label htmlFor="login-username" className="block text-sm font-medium mb-1">用户名</label>
          <input
            id="login-username"
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label htmlFor="login-password" className="block text-sm font-medium mb-1">密码</label>
          <input
            id="login-password"
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-primary py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? '登录中...' : '登录'}
        </button>
      </form>
    </div>
  )
}
