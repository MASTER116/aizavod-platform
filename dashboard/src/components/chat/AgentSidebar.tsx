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

/** Mobile-only horizontal agent selector */
export function AgentSidebar({ agents, selectedAgent, onSelect }: Props) {
  return (
    <div className="flex gap-1.5 px-3 py-2 overflow-x-auto border-b border-zinc-800 bg-zinc-950">
      <button
        className={`shrink-0 px-3 py-1.5 rounded-full text-[11px] border transition-colors ${
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
          className="shrink-0 px-3 py-1.5 rounded-full text-[11px] border transition-colors"
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
  )
}
