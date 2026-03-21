import { useState, useMemo } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import { useObservabilitySummary, useAgentStats, useDailyCosts, useSessionsSummary } from '../api/hooks'
import { parseNumeric } from '../utils/format'

export function AnalyticsPage() {
  const { data: obsSummary } = useObservabilitySummary()
  const { data: sesSummary } = useSessionsSummary()
  const { data: agentStats } = useAgentStats()

  const [days, setDays] = useState(30)
  const dateRange = useMemo(() => {
    const to = new Date()
    const from = new Date()
    from.setDate(from.getDate() - days)
    return {
      from: from.toISOString().slice(0, 10),
      to: to.toISOString().slice(0, 10),
    }
  }, [days])
  const { data: dailyCosts } = useDailyCosts(dateRange.from, dateRange.to)

  const costByAgent = useMemo(() => {
    if (!agentStats) return []
    return [...agentStats]
      .map(a => ({ name: a.agent, cost: parseNumeric(a.total_cost_usd), calls: a.total_calls }))
      .filter(a => a.cost > 0)
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 15)
  }, [agentStats])

  const qualityByAgent = useMemo(() => {
    if (!agentStats) return []
    return agentStats
      .filter(a => a.avg_quality !== 'N/A')
      .map(a => ({ name: a.agent, quality: parseNumeric(a.avg_quality) }))
      .sort((a, b) => b.quality - a.quality)
  }, [agentStats])

  const latencyByAgent = useMemo(() => {
    if (!agentStats) return []
    return [...agentStats]
      .map(a => ({ name: a.agent, latency: parseNumeric(a.avg_latency_ms) }))
      .filter(a => a.latency > 0)
      .sort((a, b) => b.latency - a.latency)
      .slice(0, 15)
  }, [agentStats])

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card label="Today Cost" value={obsSummary?.today_cost_usd || '$0'} />
        <Card label="Active Agents" value={String(obsSummary?.active_agents || 0)} />
        <Card label="Total Sessions" value={String(sesSummary?.total_sessions || 0)} />
        <Card label="Avg Duration" value={sesSummary ? `${Math.round(sesSummary.avg_duration_ms)}ms` : '—'} />
      </div>

      {/* Daily Cost Chart */}
      <div className="bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-zinc-300">Daily Cost (USD)</h3>
          <div className="flex gap-2">
            {[7, 14, 30].map(d => (
              <button
                key={d}
                className={`px-3 py-1 text-xs rounded ${days === d ? 'bg-[var(--color-zavod-gold)] text-black' : 'bg-zinc-800 text-zinc-400'}`}
                onClick={() => setDays(d)}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
        {dailyCosts && dailyCosts.length > 0 ? (
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={dailyCosts}>
              <defs>
                <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#d4a017" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#d4a017" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="date" tick={{ fill: '#71717a', fontSize: 10 }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fill: '#71717a', fontSize: 10 }} tickFormatter={v => `$${v}`} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#a1a1aa' }}
                formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']}
              />
              <Area type="monotone" dataKey="cost_usd" stroke="#d4a017" fill="url(#costGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[250px] flex items-center justify-center text-zinc-500 text-sm">No cost data</div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Cost by Agent */}
        <div className="bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Cost by Agent</h3>
          {costByAgent.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(200, costByAgent.length * 30)}>
              <BarChart data={costByAgent} layout="vertical" margin={{ left: 100 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis type="number" tick={{ fill: '#71717a', fontSize: 10 }} tickFormatter={v => `$${v}`} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#a1a1aa', fontSize: 10 }} width={100} />
                <Tooltip
                  contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: 8, fontSize: 12 }}
                  formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']}
                />
                <Bar dataKey="cost" fill="#d4a017" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-zinc-500 text-sm">No data</div>
          )}
        </div>

        {/* Quality by Agent */}
        <div className="bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Quality by Agent</h3>
          {qualityByAgent.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(200, qualityByAgent.length * 30)}>
              <BarChart data={qualityByAgent} layout="vertical" margin={{ left: 100 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis type="number" domain={[0, 10]} tick={{ fill: '#71717a', fontSize: 10 }} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#a1a1aa', fontSize: 10 }} width={100} />
                <Tooltip
                  contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: 8, fontSize: 12 }}
                  formatter={(v) => [Number(v).toFixed(1), 'Quality']}
                />
                <Bar dataKey="quality" radius={[0, 4, 4, 0]}>
                  {qualityByAgent.map((entry, i) => (
                    <Cell key={i} fill={entry.quality > 7 ? '#22c55e' : entry.quality > 5 ? '#eab308' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-zinc-500 text-sm">No quality data</div>
          )}
        </div>
      </div>

      {/* Latency by Agent */}
      <div className="bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg p-4">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Avg Latency by Agent (ms)</h3>
        {latencyByAgent.length > 0 ? (
          <ResponsiveContainer width="100%" height={Math.max(200, latencyByAgent.length * 30)}>
            <BarChart data={latencyByAgent} layout="vertical" margin={{ left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis type="number" tick={{ fill: '#71717a', fontSize: 10 }} tickFormatter={v => `${v}ms`} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#a1a1aa', fontSize: 10 }} width={100} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: 8, fontSize: 12 }}
                formatter={(v) => [`${Math.round(Number(v))}ms`, 'Latency']}
              />
              <Bar dataKey="latency" radius={[0, 4, 4, 0]}>
                {latencyByAgent.map((entry, i) => (
                  <Cell key={i} fill={entry.latency > 10000 ? '#ef4444' : entry.latency > 5000 ? '#eab308' : '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[200px] flex items-center justify-center text-zinc-500 text-sm">No latency data</div>
        )}
      </div>
    </div>
  )
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[var(--color-zavod-card)] border border-[var(--color-zavod-border)] rounded-lg p-4">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="text-xl font-bold text-zinc-200">{value}</div>
    </div>
  )
}
