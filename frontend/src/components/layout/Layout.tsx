import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { LogOut, Activity, Database, History, FlaskConical } from 'lucide-react'
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
    return <div className="min-h-screen bg-background text-foreground"><Outlet /></div>
  }

  return (
    <div className="min-h-screen bg-background font-sans text-foreground selection:bg-secondary selection:text-secondary-foreground">
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-accent" />
              <span className="font-display text-xl font-semibold tracking-tight text-primary">
                Brandiction Engine <span className="text-muted-foreground text-sm font-sans tracking-normal ml-1">v3</span>
              </span>
            </div>
            
            <nav className="hidden items-center gap-2 sm:flex">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-sm px-3 py-1.5 text-sm transition-colors ${
                    isActive
                      ? 'bg-primary/5 font-medium text-primary'
                      : 'text-muted-foreground hover:text-primary hover:bg-primary/5'
                  }`
                }
              >
                <FlaskConical className="h-4 w-4" />
                营销实验室
              </NavLink>

              {isAdmin && (
                <>
                  <NavLink
                    to="/admin/dashboard"
                    className={({ isActive }) =>
                      `flex items-center gap-1.5 rounded-sm px-3 py-1.5 text-sm transition-colors ${
                        isActive
                          ? 'bg-primary/5 font-medium text-primary'
                          : 'text-muted-foreground hover:text-primary hover:bg-primary/5'
                      }`
                    }
                  >
                    <Database className="h-4 w-4" />
                    数据总览
                  </NavLink>
                  <NavLink
                    to="/admin/history"
                    className={({ isActive }) =>
                      `flex items-center gap-1.5 rounded-sm px-3 py-1.5 text-sm transition-colors ${
                        isActive
                          ? 'bg-primary/5 font-medium text-primary'
                          : 'text-muted-foreground hover:text-primary hover:bg-primary/5'
                      }`
                    }
                  >
                    <History className="h-4 w-4" />
                    历史记录
                  </NavLink>
                </>
              )}
            </nav>
          </div>

          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="font-medium tracking-wide uppercase text-[10px]">{user.display_name}</span>
            <button
              onClick={handleLogout}
              aria-label="退出登录"
              className="flex items-center gap-1.5 transition-colors hover:text-primary"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  )
}
