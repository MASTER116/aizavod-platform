import { useState, useMemo } from 'react'
import Tree from 'react-d3-tree'
import { useRecentSessions, useSessionReplay, useSessionBlame } from '../api/hooks'
import { StatusBadge } from '../components/shared/StatusBadge'
import { formatDuration, formatCost, formatDate } from '../utils/format'
import type { TimelineEntry } from '../api/types'

interface TreeNodeData {
  name: string
  attributes?: Record<string, string>
  children?: TreeNodeData[]
  _status?: string
}

function buildTree(timeline: TimelineEntry[]): TreeNodeData | null {
  if (!timeline.length) return null

  const map = new Map<string, TreeNodeData & { _raw: TimelineEntry }>()
  for (const e of timeline) {
    map.set(e.span_id, {
      name: `${e.agent || 'conductor'}.${e.operation}`,
      attributes: {
        status: e.status,
        duration: formatDuration(e.duration_ms),
        cost: formatCost(e.cost_usd),
        tokens: String(e.tokens),
      },
      children: [],
      _status: e.status,
      _raw: e,
    })
  }

  let root: TreeNodeData | null = null
  for (const e of timeline) {
    const node = map.get(e.span_id)!
    if (e.parent_span_id && map.has(e.parent_span_id)) {
      map.get(e.parent_span_id)!.children!.push(node)
    } else if (!root) {
      root = node
    }
  }
  return root || map.values().next().value || null
}

export function TreePage() {
  const { data: sessions } = useRecentSessions(30)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data: replay } = useSessionReplay(selectedId)
  const { data: blame } = useSessionBlame(selectedId)

  const tree = useMemo(() => {
    if (!replay?.timeline) return null
    return buildTree(replay.timeline)
  }, [replay])

  return (
    <div className="flex gap-4 h-[calc(100vh-8rem)]">
      {/* Session list */}
      <div className="w-80 flex-shrink-0 bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg overflow-auto">
        <div className="p-3 border-b border-zinc-800 text-sm font-medium text-zinc-300">Recent Sessions</div>
        {sessions?.map(s => (
          <button
            key={s.correlation_id}
            className={`w-full text-left p-3 border-b border-zinc-800/50 hover:bg-zinc-900 transition-colors ${
              selectedId === s.correlation_id ? 'bg-zinc-900 border-l-2 border-l-[var(--color-zavod-gold)]' : ''
            }`}
            onClick={() => setSelectedId(s.correlation_id)}
          >
            <div className="text-xs text-zinc-300 truncate mb-1">{s.query || '(empty)'}</div>
            <div className="flex items-center gap-2 text-[10px]">
              <StatusBadge status={s.status} />
              <span className="text-zinc-500">{formatDuration(s.duration_ms)}</span>
              <span className="text-zinc-500">{formatCost(s.cost_usd)}</span>
              <span className="text-zinc-500">{s.agents} agents</span>
            </div>
            <div className="text-[10px] text-zinc-600 mt-1">{formatDate(s.started_at)}</div>
          </button>
        ))}
        {!sessions?.length && <div className="p-4 text-xs text-zinc-500 text-center">No sessions yet</div>}
      </div>

      {/* Tree + details */}
      <div className="flex-1 flex flex-col gap-4">
        {replay && (
          <>
            {/* Session info bar */}
            <div className="bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg p-4 flex items-center gap-6 text-xs">
              <div>
                <span className="text-zinc-500">Mode: </span>
                <span className="text-zinc-200">{replay.mode}</span>
              </div>
              <div>
                <span className="text-zinc-500">Duration: </span>
                <span className="text-zinc-200">{formatDuration(replay.total_duration_ms)}</span>
              </div>
              <div>
                <span className="text-zinc-500">Cost: </span>
                <span className="text-zinc-200">{formatCost(replay.total_cost_usd)}</span>
              </div>
              <div>
                <span className="text-zinc-500">Tokens: </span>
                <span className="text-zinc-200">{replay.total_tokens.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-zinc-500">Agents: </span>
                <span className="text-zinc-200">{replay.agent_chain.join(' → ')}</span>
              </div>
              <StatusBadge status={replay.status} />
            </div>

            {/* Timeline bar */}
            {replay.timeline.length > 0 && replay.total_duration_ms > 0 && (
              <div className="bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg p-3">
                <div className="text-[10px] text-zinc-500 mb-2">Timeline</div>
                <div className="relative h-6 bg-zinc-800 rounded overflow-hidden">
                  {replay.timeline.map((t, i) => {
                    const left = (t.offset_ms / replay.total_duration_ms) * 100
                    const width = Math.max((t.duration_ms / replay.total_duration_ms) * 100, 1)
                    const color = t.status === 'error' ? '#ef4444' : t.status === 'success' ? '#22c55e' : '#3b82f6'
                    return (
                      <div
                        key={i}
                        className="absolute top-0.5 h-5 rounded-sm opacity-80"
                        style={{ left: `${left}%`, width: `${width}%`, background: color, minWidth: '3px' }}
                        title={`${t.agent}.${t.operation} — ${formatDuration(t.duration_ms)}`}
                      />
                    )
                  })}
                </div>
              </div>
            )}

            {/* Tree visualization */}
            {tree && (
              <div className="flex-1 bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg overflow-hidden">
                <Tree
                  data={tree}
                  orientation="vertical"
                  pathFunc="step"
                  translate={{ x: 300, y: 50 }}
                  nodeSize={{ x: 220, y: 100 }}
                  separation={{ siblings: 1.2, nonSiblings: 1.5 }}
                  renderCustomNodeElement={({ nodeDatum }) => {
                    const attrs = nodeDatum.attributes || {}
                    const st = attrs.status as string
                    const col = st === 'error' ? '#ef4444' : st === 'success' ? '#22c55e' : st === 'running' ? '#3b82f6' : '#71717a'
                    return (
                      <g>
                        <rect x="-90" y="-20" width="180" height="48" rx="6" fill="#18181b" stroke={col} strokeWidth={1.5} />
                        <text x="0" y="-2" textAnchor="middle" fill="#e4e4e7" fontSize="10" fontFamily="Inter, sans-serif">
                          {String(nodeDatum.name).slice(0, 25)}
                        </text>
                        <text x="0" y="16" textAnchor="middle" fill="#71717a" fontSize="9" fontFamily="Inter, sans-serif">
                          {attrs.duration} | {attrs.cost} | {attrs.tokens}t
                        </text>
                        <circle cx="80" cy="-12" r="4" fill={col} />
                      </g>
                    )
                  }}
                />
              </div>
            )}
            {!tree && <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">No spans in this session</div>}

            {/* Blame view */}
            {blame && (blame.total_errors > 0 || blame.slowest_agent) && (
              <div className="bg-zinc-950 border border-[var(--color-zavod-border)] rounded-lg p-4">
                <div className="text-xs font-medium text-zinc-300 mb-2">Blame Analysis</div>
                <div className="flex gap-6 text-xs">
                  {blame.error_agents.map((ea, i) => (
                    <div key={i} className="text-red-400">
                      <span className="font-medium">{ea.agent}</span>.{ea.operation}: {ea.error || 'error'}
                    </div>
                  ))}
                  {blame.slowest_agent && (
                    <div className="text-amber-400">
                      Slowest: <span className="font-medium">{blame.slowest_agent.agent}</span> — {formatDuration(blame.slowest_agent.duration_ms)}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
        {!selectedId && (
          <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">
            Select a session from the list
          </div>
        )}
      </div>
    </div>
  )
}
