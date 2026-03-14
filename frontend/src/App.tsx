import { useState, useEffect } from 'react'
import { createHashRouter, Navigate, RouterProvider } from 'react-router-dom'

import { getMe, type AuthUser } from './lib/api'
import { Layout } from './components/layout/Layout'
import { LoginPage } from './pages/LoginPage'
import { HomePage } from './pages/HomePage'
import { RunningPage } from './pages/RunningPage'
import { ResultPage } from './pages/ResultPage'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'

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
