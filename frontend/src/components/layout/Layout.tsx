import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { logout as logoutApi, type AuthUser } from '../../lib/api'

export function Layout({
  user,
  onLogout,
}: {
  user: AuthUser
  onLogout: () => void
}) {
  const location = useLocation()
  const isAdmin = user.role === 'admin'

  const handleLogout = async () => {
    try {
      await logoutApi()
    } catch {
      // ignore
    }
    onLogout()
  }

  // Running page: immersive, no header
  if (location.pathname === '/running') {
    return <Outlet />
  }

  return (
    <div className="min-h-screen bg-[#FDFCFB] font-sans text-stone-900 selection:bg-stone-200">
      <header className="sticky top-0 z-10 border-b border-stone-200/50 bg-[#FDFCFB]/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold tracking-tight">MiroFishmoody</span>
            {isAdmin && (
              <nav className="hidden items-center gap-1 sm:flex">
                <NavLink
                  to="/admin/dashboard"
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-sm transition-colors ${
                      isActive
                        ? 'bg-stone-100 font-medium text-stone-900'
                        : 'text-stone-500 hover:text-stone-700'
                    }`
                  }
                >
                  总览台
                </NavLink>
                <NavLink
                  to="/admin/history"
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-sm transition-colors ${
                      isActive
                        ? 'bg-stone-100 font-medium text-stone-900'
                        : 'text-stone-500 hover:text-stone-700'
                    }`
                  }
                >
                  结算历史
                </NavLink>
              </nav>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm text-stone-500">
            <span>{user.display_name}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 transition-colors hover:text-stone-900"
            >
              <LogOut className="h-4 w-4" />
              退出
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
