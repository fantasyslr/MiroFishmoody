import { NavLink, Outlet } from 'react-router-dom'

import { navigation } from '../../data/campaignDecisionData'

export function AppShell() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-cream text-coffee">
      <div className="ambient-orb ambient-orb-left" />
      <div className="ambient-orb ambient-orb-right" />

      <header className="sticky top-0 z-40 border-b border-line/70 bg-paper/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="section-label">Moody 内部 campaign 决策市场</p>
              <div className="mt-2 flex items-end gap-3">
                <h1 className="font-serif text-3xl font-semibold tracking-tight text-coffee sm:text-4xl">
                  MiroFishmoody
                </h1>
                <span className="mb-1 rounded-full border border-mist/25 bg-mist-soft/70 px-3 py-1 text-xs font-semibold text-mist">
                  前端示例壳
                </span>
              </div>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/80">
                用统一的中文信息结构，把评审、结果和结算收进同一套前端语言里。
              </p>
            </div>

            <div className="flex flex-wrap gap-2 text-xs text-ink/80">
              <span className="rounded-full border border-line bg-cream px-3 py-2">中文优先</span>
              <span className="rounded-full border border-line bg-cream px-3 py-2">示例数据</span>
              <span className="rounded-full border border-line bg-cream px-3 py-2">React + Tailwind</span>
            </div>
          </div>

          <nav className="flex gap-2 overflow-x-auto pb-1">
            {navigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `min-w-fit rounded-full border px-4 py-2.5 text-sm transition ${
                    isActive
                      ? 'border-coffee bg-coffee text-paper shadow-card'
                      : 'border-line bg-paper/70 text-ink hover:border-mist hover:text-coffee'
                  }`
                }
              >
                <span className="block font-semibold">{item.label}</span>
                <span className="mt-0.5 block text-xs opacity-75">{item.description}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
