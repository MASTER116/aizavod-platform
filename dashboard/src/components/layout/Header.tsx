import { useAgentSummary } from '../../api/hooks'

export function Header() {
  const { data } = useAgentSummary()

  return (
    <header className="h-14 border-b border-[var(--color-zavod-border)] flex items-center justify-between px-6 bg-zinc-950/80 backdrop-blur">
      <div />
      {data && (
        <div className="flex items-center gap-4 text-xs">
          <Pill color="#22c55e" label="Healthy" count={data.healthy} />
          <Pill color="#eab308" label="Degraded" count={data.degraded} />
          <Pill color="#ef4444" label="Unhealthy" count={data.unhealthy} />
          <Pill color="#71717a" label="Killed" count={data.killed} />
          <span className="text-zinc-500">|</span>
          <span className="text-zinc-400">Calls: {data.total_calls}</span>
        </div>
      )}
    </header>
  )
}

function Pill({ color, label, count }: { color: string; label: string; count: number }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full" style={{ background: color }} />
      <span className="text-zinc-400">{label}</span>
      <span className="font-medium text-zinc-200">{count}</span>
    </span>
  )
}
