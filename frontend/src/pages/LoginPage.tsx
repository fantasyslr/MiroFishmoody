import { useState } from 'react'
import { motion } from 'motion/react'
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
    <div className="flex min-h-screen items-center justify-center bg-[#FDFCFB] p-6 font-sans text-stone-900">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm"
      >
        <div className="mb-10 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">MiroFishmoody</h1>
          <p className="mt-2 text-sm text-stone-500">内部营销决策工具</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
              {error}
            </div>
          )}
          <input
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            className="w-full rounded-xl border border-stone-200 bg-white px-4 py-3 outline-none transition-all placeholder:text-stone-400 focus:border-stone-400 focus:ring-1 focus:ring-stone-400"
          />
          <input
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-stone-200 bg-white px-4 py-3 outline-none transition-all placeholder:text-stone-400 focus:border-stone-400 focus:ring-1 focus:ring-stone-400"
          />
          <button
            type="submit"
            disabled={!username.trim() || !password || loading}
            className="mt-2 w-full rounded-xl bg-stone-900 py-3 font-medium text-white transition-colors hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
      </motion.div>
    </div>
  )
}
