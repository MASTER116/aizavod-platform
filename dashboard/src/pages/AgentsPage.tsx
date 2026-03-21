import { useState, useMemo } from 'react'
import { useAgentHealth, useAgentRegistry, useAgentSummary, useKillAgent, useReviveAgent, useSuspendAgent } from '../api/hooks'
import type { MergedAgent } from '../api/types'
import { StatusBadge } from '../components/shared/StatusBadge'
import { ConfirmDialog } from '../components/shared/ConfirmDialog'

export function AgentsPage() {
  const { data: health } = useAgentHealth()
  const { data: registry } = useAgentRegistry()
  const { data: summary } = useAgentSummary()
  const killMut = useKillAgent()
  const reviveMut = useReviveAgent()
  const suspendMut = useSuspendAgent()

  const [filterDept, setFilterDept] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [search, setSearch] = useState('')
  const [dialog, setDialog] = useState<{ type: 'kill' | 'suspend' | 'revive'; name: string } | null>(null)

  const agents = useMemo<MergedAgent[]>(() => {
    if (!registry) return []
    const healthMap = new Map((health || []).map(h => [h.name, h]))
    return registry.map(r => ({ ...r, health: healthMap.get(r.name) }))
  }, [registry, health])

  const departments = useMemo(() => [...new Set(agents.map(a => a.department))].sort(), [agents])

  const filtered = useMemo(() => {
    return agents.filter(a => {
      if (filterDept && a.department !== filterDept) return false
      if (filterStatus && a.health?.status !== filterStatus) return false
      if (search) {
        const q = search.toLowerCase()
        if (!a.name.includes(q) && !a.title.toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [agents, filterDept, filterStatus, search])

  return (
    <div>
      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <SummaryCard label="Total" value={summary.total_agents} />
          <SummaryCard label="Healthy" value={summary.healthy} color="#22c55e" />
          <SummaryCard label="Degraded" value={summary.degraded} color="#eab308" />
          <SummaryCard label="Unhealthy" value={summary.unhealthy} color="#ef4444" />
          <SummaryCard label="Killed" value={summary.killed} color="#71717a" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 w-48"
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-300"
          value={filterDept}
          onChange={e => setFilterDept(e.target.value)}
        >
          <option value="">All departments</option>
          {departments.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-300"
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          {['healthy', 'degraded', 'unhealthy', 'killed', 'suspended', 'retired'].map(s =>
            <option key={s} value={s}>{s}</option>
          )}
        </select>
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filtered.map(a => (
          <AgentCard
            key={a.name}
            agent={a}
            onKill={() => setDialog({ type: 'kill', name: a.name })}
            onSuspend={() => setDialog({ type: 'suspend', name: a.name })}
            onRevive={() => setDialog({ type: 'revive', name: a.name })}
          />
        ))}
      </div>
      {filtered.length === 0 && <p className="text-zinc-500 text-center py-12">No agents match filters</p>}

      {/* Dialogs */}
      {dialog?.type === 'kill' && (
        <ConfirmDialog
          title={`Kill ${dialog.name}`}
          message="This will stop the agent from handling any requests."
          needReason
          confirmLabel="Kill Agent"
          confirmColor="#ef4444"
          onConfirm={reason => { killMut.mutate({ name: dialog.name, reason }); setDialog(null) }}
          onCancel={() => setDialog(null)}
        />
      )}
      {dialog?.type === 'suspend' && (
        <ConfirmDialog
          title={`Suspend ${dialog.name}`}
          message="Agent will be paused and won't receive new tasks."
          needReason
          confirmLabel="Suspend"
          confirmColor="#6366f1"
          onConfirm={reason => { suspendMut.mutate({ name: dialog.name, reason }); setDialog(null) }}
          onCancel={() => setDialog(null)}
        />
      )}
      {dialog?.type === 'revive' && (
        <ConfirmDialog
          title={`Revive ${dialog.name}`}
          message="This will restore the agent to healthy status."
          confirmLabel="Revive"
          confirmColor="#22c55e"
          onConfirm={() => { reviveMut.mutate(dialog.name); setDialog(null) }}
          onCancel={() => setDialog(null)}
        />
      )}
    </div>
  )
}

function SummaryCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-[var(--color-zavod-card)] border border-[var(--color-zavod-border)] rounded-lg p-4">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color || 'var(--color-zavod-text)' }}>{value}</div>
    </div>
  )
}

function AgentCard({ agent, onKill, onSuspend, onRevive }: {
  agent: MergedAgent
  onKill: () => void
  onSuspend: () => void
  onRevive: () => void
}) {
  const h = agent.health
  const status = h?.status || 'pending'

  return (
    <div className="bg-[var(--color-zavod-card)] border border-[var(--color-zavod-border)] rounded-lg p-4 hover:border-zinc-600 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="font-medium text-sm">{agent.title}</div>
          <div className="text-xs text-zinc-500">{agent.name}</div>
        </div>
        <StatusBadge status={status} />
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">{agent.department}</span>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">{agent.access_level}</span>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-[var(--color-zavod-gold)]">
          {agent.credit_cost} cr
        </span>
      </div>

      {h && (
        <div className="grid grid-cols-3 gap-2 text-xs mb-3">
          <div>
            <span className="text-zinc-500">Calls</span>
            <div className="font-medium">{h.total_calls}</div>
          </div>
          <div>
            <span className="text-zinc-500">Errors</span>
            <div className="font-medium" style={{ color: h.total_errors > 0 ? '#ef4444' : undefined }}>{h.error_rate}</div>
          </div>
          <div>
            <span className="text-zinc-500">Latency</span>
            <div className="font-medium">{h.avg_latency_ms}ms</div>
          </div>
        </div>
      )}

      {h?.last_error && (
        <div className="text-[10px] text-red-400 truncate mb-2" title={h.last_error}>{h.last_error}</div>
      )}

      <div className="flex gap-2 pt-2 border-t border-zinc-800">
        {(status === 'healthy' || status === 'degraded') && (
          <>
            <ActionBtn label="Kill" color="#ef4444" onClick={onKill} />
            <ActionBtn label="Suspend" color="#6366f1" onClick={onSuspend} />
          </>
        )}
        {(status === 'killed' || status === 'unhealthy' || status === 'suspended' || status === 'retired') && (
          <ActionBtn label="Revive" color="#22c55e" onClick={onRevive} />
        )}
      </div>
    </div>
  )
}

function ActionBtn({ label, color, onClick }: { label: string; color: string; onClick: () => void }) {
  return (
    <button
      className="px-3 py-1 text-[10px] font-medium rounded border transition-colors"
      style={{ borderColor: color + '44', color, background: color + '11' }}
      onClick={onClick}
    >
      {label}
    </button>
  )
}
