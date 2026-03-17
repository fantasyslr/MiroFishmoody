import { useState, useEffect } from 'react'
import { createHashRouter, Navigate, RouterProvider } from 'react-router-dom'

import { getMe, type AuthUser } from './lib/api'
import { Layout } from './components/layout/Layout'
import { LoginPage } from './pages/LoginPage'
import { HomePage } from './pages/HomePage'
import { RunningPage } from './pages/RunningPage'
import { ResultPage } from './pages/ResultPage'
import { EvaluatePage } from './pages/EvaluatePage'
import { EvaluateResultPage } from './pages/EvaluateResultPage'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'
import { CompareVersionPage } from './pages/CompareVersionPage'
import { TrendDashboardPage } from './pages/TrendDashboardPage'

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

  const isAdmin = user.role === 'admin'

  const routes = [
    {
      element: <Layout user={user} onLogout={() => setUser(null)} />,
      children: [
        { path: '/', element: <HomePage /> },
        { path: '/running', element: <RunningPage /> },
        { path: '/result', element: <ResultPage /> },
        { path: '/evaluate', element: <EvaluatePage /> },
        { path: '/evaluate-result', element: <EvaluateResultPage /> },
        { path: '/compare', element: <CompareVersionPage /> },
        { path: '/trends', element: <TrendDashboardPage /> },
        // Admin routes integrated into the same layout
        ...(isAdmin
          ? [
              { path: '/admin/dashboard', element: <DashboardPage /> },
              { path: '/admin/history', element: <HistoryPage /> },
            ]
          : []),
      ],
    },
    { path: '*', element: <Navigate to="/" replace /> },
  ]

  const router = createHashRouter(routes)

  return <RouterProvider router={router} />
}
