import { NavLink, Outlet } from 'react-router-dom'

import { logout as logoutApi, type AuthUser } from '../../lib/api'

const adminNav = [
  { to: '/admin/dashboard', label: '总览台' },
  { to: '/admin/history', label: '结算历史' },
  { to: '/', label: '新建评审' },
]

export function AppShell({ user, onLogout }: { user?: AuthUser; onLogout?: () => void }) {
  const handleLogout = async () => {
    try {
      await logoutApi()
    } catch {
      // ignore
    }
    onLogout?.()
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-cream text-coffee">
      <div className="ambient-orb ambient-orb-left" />
      <div className="ambient-orb ambient-orb-right" />

      <header className="sticky top-0 z-40 border-b border-line/70 bg-paper/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="font-serif text-2xl font-semibold tracking-tight text-coffee">
                MiroFishmoody
              </h1>
              <span className="rounded-full border border-mist/25 bg-mist-soft/70 px-3 py-1 text-xs font-semibold text-mist">
                管理后台
              </span>
            </div>

            <div className="flex items-center gap-4">
              {user && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-ink/70">{user.display_name}</span>
                  <button
                    className="secondary-button text-xs"
                    type="button"
                    onClick={handleLogout}
                  >
                    退出
                  </button>
                </div>
              )}
            </div>
          </div>

          <nav className="flex gap-2">
            {adminNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-full border px-4 py-2 text-sm font-semibold transition-all duration-200 ${
                    isActive
                      ? 'border-coffee bg-coffee text-paper shadow-card'
                      : 'border-line bg-paper/70 text-ink hover:border-mist hover:bg-paper hover:text-coffee'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="page-enter relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
