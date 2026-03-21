const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  healthy: { label: 'Healthy', color: '#22c55e', bg: 'rgba(34,197,94,0.1)' },
  degraded: { label: 'Degraded', color: '#eab308', bg: 'rgba(234,179,8,0.1)' },
  unhealthy: { label: 'Unhealthy', color: '#ef4444', bg: 'rgba(239,68,68,0.1)' },
  killed: { label: 'Killed', color: '#71717a', bg: 'rgba(113,113,122,0.1)' },
  suspended: { label: 'Suspended', color: '#6366f1', bg: 'rgba(99,102,241,0.1)' },
  retired: { label: 'Retired', color: '#78716c', bg: 'rgba(120,113,108,0.1)' },
  success: { label: 'Success', color: '#22c55e', bg: 'rgba(34,197,94,0.1)' },
  error: { label: 'Error', color: '#ef4444', bg: 'rgba(239,68,68,0.1)' },
  running: { label: 'Running', color: '#3b82f6', bg: 'rgba(59,130,246,0.1)' },
  timeout: { label: 'Timeout', color: '#f97316', bg: 'rgba(249,115,22,0.1)' },
  pending: { label: 'Pending', color: '#71717a', bg: 'rgba(113,113,122,0.1)' },
  partial: { label: 'Partial', color: '#eab308', bg: 'rgba(234,179,8,0.1)' },
}

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}33` }}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5" style={{ background: cfg.color }} />
      {cfg.label}
    </span>
  )
}
