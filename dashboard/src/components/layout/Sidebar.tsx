import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/chat', label: 'Chat', icon: '💬' },
  { to: '/agents', label: 'Agents', icon: '🤖' },
  { to: '/tree', label: 'Tasks', icon: '🌳' },
  { to: '/analytics', label: 'Analytics', icon: '📊' },
]

export function Sidebar() {
  return (
    <aside className="w-56 h-screen flex flex-col border-r border-[var(--color-zavod-border)] bg-zinc-950 fixed left-0 top-0">
      <div className="p-4 border-b border-[var(--color-zavod-border)]">
        <div className="flex items-center gap-2">
          <span className="text-xl">🏭</span>
          <span className="font-bold text-sm bg-gradient-to-r from-[var(--color-zavod-gold)] to-[var(--color-zavod-gold-light)] bg-clip-text text-transparent">
            ZAVOD-II
          </span>
        </div>
        <div className="text-[10px] text-zinc-500 mt-1">Agent Dashboard</div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(n => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-[var(--color-zavod-card)] text-[var(--color-zavod-gold)] border border-[var(--color-zavod-border)]'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
              }`
            }
          >
            <span>{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-[var(--color-zavod-border)]">
        <button
          className="w-full text-xs text-zinc-500 hover:text-zinc-300 py-2"
          onClick={() => {
            localStorage.removeItem('zavod_token')
            window.location.hash = '#/login'
            window.location.reload()
          }}
        >
          Logout
        </button>
      </div>
    </aside>
  )
}
