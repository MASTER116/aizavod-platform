import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuth } from './hooks/useAuth'
import { Layout } from './components/layout/Layout'
import { LoginPage } from './pages/LoginPage'
import { AgentsPage } from './pages/AgentsPage'
import { TreePage } from './pages/TreePage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { ChatPage } from './pages/ChatPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

function AppRoutes() {
  const { isAuthenticated, login } = useAuth()

  if (!isAuthenticated) {
    return <LoginPage onLogin={login} />
  }

  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:agentName" element={<ChatPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/tree" element={<TreePage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Route>
      </Routes>
    </HashRouter>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRoutes />
    </QueryClientProvider>
  )
}
