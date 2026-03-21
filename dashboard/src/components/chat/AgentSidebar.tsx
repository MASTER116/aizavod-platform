export interface AgentPersona {
  name: string
  title: string
  department: string
  description: string
  avatar: string
  color: string
  style: string
  quick_actions: string[]
  access_level: string
}

interface Props {
  agents: AgentPersona[]
  selectedAgent?: string | null
  onSelect: (name: string | null) => void
}

export function AgentSidebar({ agents, selectedAgent, onSelect }: Props) {
  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:flex flex-col w-56 border-l border-zinc-800 bg-zinc-950 overflow-y-auto">
        <div className="p-3 border-b border-zinc-800 text-xs font-medium text-zinc-400">
          Agents ({agents.length})
        </div>
        <button
          className={`w-full text-left px-3 py-2 text-xs transition-colors ${
            !selectedAgent ? 'bg-zinc-900 text-[var(--color-zavod-gold)]' : 'text-zinc-400 hover:bg-zinc-900'
          }`}
          onClick={() => onSelect(null)}
        >
          🏭 Team Chat (auto-route)
        </button>
        {agents.map(a => (
          <button
            key={a.name}
            className={`w-full text-left px-3 py-2 flex items-center gap-2 transition-colors ${
              selectedAgent === a.name
                ? 'bg-zinc-900 border-l-2'
                : 'text-zinc-400 hover:bg-zinc-900/50'
            }`}
            style={selectedAgent === a.name ? { borderLeftColor: a.color, color: a.color } : {}}
            onClick={() => onSelect(a.name)}
          >
            <span className="text-sm">{a.avatar}</span>
            <div className="min-w-0">
              <div className="text-xs truncate">{a.title}</div>
              <div className="text-[10px] text-zinc-600 truncate">{a.department}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Mobile horizontal list */}
      <div className="lg:hidden flex gap-1 px-3 py-2 overflow-x-auto border-b border-zinc-800 bg-zinc-950">
        <button
          className={`shrink-0 px-3 py-1.5 rounded-full text-[10px] border transition-colors ${
            !selectedAgent
              ? 'border-[var(--color-zavod-gold)]/40 text-[var(--color-zavod-gold)] bg-[var(--color-zavod-gold)]/10'
              : 'border-zinc-700 text-zinc-400'
          }`}
          onClick={() => onSelect(null)}
        >
          🏭 Auto
        </button>
        {agents.map(a => (
          <button
            key={a.name}
            className="shrink-0 px-3 py-1.5 rounded-full text-[10px] border transition-colors"
            style={
              selectedAgent === a.name
                ? { borderColor: a.color + '66', color: a.color, background: a.color + '15' }
                : { borderColor: '#3f3f46', color: '#a1a1aa' }
            }
            onClick={() => onSelect(a.name)}
          >
            {a.avatar} {a.title}
          </button>
        ))}
      </div>
    </>
  )
}
