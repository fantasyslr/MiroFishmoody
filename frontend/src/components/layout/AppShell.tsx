import { NavLink, Outlet } from 'react-router-dom'

import { logout as logoutApi, type AuthUser } from '../../lib/api'
import { navigation } from '../../data/campaignDecisionData'

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
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="section-label">Moody 内部 campaign 评审工作台</p>
              <div className="mt-2 flex items-end gap-3">
                <h1 className="font-serif text-3xl font-semibold tracking-tight text-coffee sm:text-4xl">
                  MiroFishmoody
                </h1>
                <span className="mb-1 rounded-full border border-mist/25 bg-mist-soft/70 px-3 py-1 text-xs font-semibold text-mist">
                  内部试用版
                </span>
              </div>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/80">
                用统一的中文信息结构，把评审、结果和结算收进同一套前端语言里，并优先接通真实后端流程。
              </p>
            </div>

            <div className="flex items-center gap-4">
              <div className="hidden flex-wrap gap-2 text-xs text-ink/80 sm:flex">
                <span className="rounded-full border border-line bg-cream px-3 py-2">中文优先</span>
                <span className="rounded-full border border-line bg-cream px-3 py-2">联调中</span>
                <span className="rounded-full border border-line bg-cream px-3 py-2">React + Tailwind</span>
              </div>
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

          <div className="nav-scroll-fade relative -mb-px">
            <nav className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
              {navigation.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `min-w-fit rounded-full border px-4 py-2.5 text-sm transition-all duration-200 ${
                      isActive
                        ? 'border-coffee bg-coffee text-paper shadow-card'
                        : 'border-line bg-paper/70 text-ink hover:border-mist hover:bg-paper hover:text-coffee active:scale-[0.97]'
                    }`
                  }
                >
                  <span className="block font-semibold">{item.label}</span>
                  <span className="mt-0.5 hidden text-xs opacity-75 sm:block">{item.description}</span>
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </header>

      <main className="page-enter relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <Outlet />
      </main>

      <footer className="relative z-10 border-t border-line/50 py-6 text-center text-xs text-ink/50">
        <p>MiroFishmoody · 内部试用版 · 关键路径已接真实后端，部分说明区仍为占位文案</p>
      </footer>
    </div>
  )
}
