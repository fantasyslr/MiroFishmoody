import { createHashRouter, RouterProvider } from 'react-router-dom'

import { AppShell } from './components/layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'
import { NewReviewPage } from './pages/NewReviewPage'
import { ResultPage } from './pages/ResultPage'
import { RunningStatusPage } from './pages/RunningStatusPage'

const router = createHashRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'new-review', element: <NewReviewPage /> },
      { path: 'running', element: <RunningStatusPage /> },
      { path: 'result', element: <ResultPage /> },
      { path: 'history', element: <HistoryPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
