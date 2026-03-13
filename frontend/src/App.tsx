import { useState, useEffect } from 'react'
import { createHashRouter, RouterProvider } from 'react-router-dom'

import { getMe, type AuthUser } from './lib/api'
import { AppShell } from './components/layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'
import { LoginPage } from './pages/LoginPage'
import { NewReviewPage } from './pages/NewReviewPage'
import { ResultPage } from './pages/ResultPage'
import { RunningStatusPage } from './pages/RunningStatusPage'

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  if (checking) return null

  if (!user) {
    return <LoginPage onLogin={setUser} />
  }

  const router = createHashRouter([
    {
      path: '/',
      element: <AppShell user={user} onLogout={() => setUser(null)} />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'new-review', element: <NewReviewPage /> },
        { path: 'running', element: <RunningStatusPage /> },
        { path: 'result', element: <ResultPage /> },
        { path: 'history', element: <HistoryPage /> },
      ],
    },
  ])

  return <RouterProvider router={router} />
}
