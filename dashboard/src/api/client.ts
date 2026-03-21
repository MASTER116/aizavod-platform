const BASE = ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('zavod_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    localStorage.removeItem('zavod_token')
    window.location.hash = '#/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<{ access_token: string }>('/admin/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  // Agent Health
  agentsHealth: () => request<any[]>('/admin/api/dashboard/agents/health'),
  agentsSummary: () => request<any>('/admin/api/dashboard/agents/summary'),
  agentsAudit: (limit = 50) => request<any[]>(`/admin/api/dashboard/agents/audit?limit=${limit}`),
  agentKill: (name: string, reason: string) =>
    request<any>(`/admin/api/dashboard/agents/${name}/kill`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  agentRevive: (name: string) =>
    request<any>(`/admin/api/dashboard/agents/${name}/revive`, { method: 'POST' }),
  agentSuspend: (name: string, reason: string) =>
    request<any>(`/admin/api/dashboard/agents/${name}/suspend`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  // Registry & Hierarchy
  agentsRegistry: () => request<any[]>('/admin/api/dashboard/agents/registry'),
  hierarchy: () => request<any>('/admin/api/dashboard/hierarchy'),

  // Observability
  observabilitySummary: () => request<any>('/admin/api/dashboard/observability/summary'),
  observabilityAgents: () => request<any[]>('/admin/api/dashboard/observability/agents'),
  dailyCosts: (from: string, to: string) =>
    request<any[]>(`/admin/api/dashboard/observability/daily-costs?from=${from}&to=${to}`),

  // Sessions
  sessionsRecent: (limit = 20) => request<any[]>(`/admin/api/dashboard/sessions/recent?limit=${limit}`),
  sessionsSummary: () => request<any>('/admin/api/dashboard/sessions/summary'),
  sessionReplay: (id: string) => request<any>(`/admin/api/dashboard/sessions/${id}/replay`),
  sessionBlame: (id: string) => request<any>(`/admin/api/dashboard/sessions/${id}/blame`),
}
