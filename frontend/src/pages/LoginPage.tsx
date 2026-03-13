import { useState } from 'react'
import { login, type AuthUser } from '../lib/api'

export function LoginPage({ onLogin }: { onLogin: (user: AuthUser) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) return
    setLoading(true)
    setError('')
    try {
      const user = await login(username.trim(), password)
      onLogin(user)
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-linen">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-5 rounded-panel border border-line bg-paper p-8 shadow-paper"
      >
        <div className="text-center">
          <h1 className="font-serif text-2xl font-semibold text-coffee">Moody Campaign Engine</h1>
          <p className="mt-2 text-sm text-ink/60">内部评审系统，请登录</p>
        </div>

        {error && (
          <div className="rounded-2xl border border-wine/20 bg-wine/10 px-4 py-3 text-sm text-wine">
            {error}
          </div>
        )}

        <label className="block space-y-2">
          <span className="field-label">用户名</span>
          <input
            className="field-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="请输入用户名"
            autoFocus
          />
        </label>

        <label className="block space-y-2">
          <span className="field-label">密码</span>
          <input
            className="field-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="请输入密码"
          />
        </label>

        <button
          className="primary-button w-full justify-center"
          type="submit"
          disabled={loading || !username.trim() || !password}
        >
          {loading ? '登录中...' : '登录'}
        </button>
      </form>
    </div>
  )
}
