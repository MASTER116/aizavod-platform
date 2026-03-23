import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function Layout() {
  const { pathname } = useLocation()
  const isChat = pathname.startsWith('/chat')

  return (
    <div className="flex min-h-screen bg-[var(--color-zavod-bg)]">
      <Sidebar />
      <div className="flex-1 ml-56 flex flex-col">
        <Header />
        {isChat ? (
          <div className="flex-1 flex flex-col min-h-0">
            <Outlet />
          </div>
        ) : (
          <main className="p-6 flex-1">
            <Outlet />
          </main>
        )}
      </div>
    </div>
  )
}
