// Agent health from HealthMonitor
export interface AgentHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy' | 'killed' | 'suspended' | 'retired'
  total_calls: number
  total_errors: number
  error_rate: string
  avg_latency_ms: string
  last_error: string
  kill_reason: string
  is_alive: boolean
}

// Agent registry (static metadata)
export interface AgentRegistryEntry {
  name: string
  title: string
  department: string
  description: string
  access_level: 'simple' | 'pro' | 'enterprise'
  tier: string
  credit_cost: number
  criticality: string
}

// Health summary
export interface HealthSummary {
  total_agents: number
  healthy: number
  degraded: number
  unhealthy: number
  killed: number
  total_calls: number
  total_errors: number
  killed_agents: string[]
}

// Audit log entry
export interface AuditEntry {
  timestamp: string
  action: string
  agent: string
  details: string
}

// Observability summary
export interface ObservabilitySummary {
  total_traces: number
  today_cost_usd: string
  today_alert_threshold: string
  active_agents: number
  total_users_today: number
}

// Agent stats from ObservabilityTracker
export interface AgentStats {
  agent: string
  total_calls: number
  error_rate: string
  total_cost_usd: string
  avg_latency_ms: string
  avg_quality: string
}

// Daily cost
export interface DailyCost {
  date: string
  cost_usd: number
}

// Session (recent list)
export interface SessionItem {
  correlation_id: string
  user_id: number | null
  query: string
  status: string
  mode: string
  agents: number
  duration_ms: number
  cost_usd: number
  errors: number
  started_at: string
}

// Session replay
export interface TimelineEntry {
  span_id: string
  parent_span_id: string | null
  agent: string
  operation: string
  input: string
  output: string
  status: string
  error: string
  offset_ms: number
  duration_ms: number
  model: string
  tokens: number
  cost_usd: number
}

export interface SessionReplay {
  correlation_id: string
  user_id: number | null
  channel: string
  query: string
  final_response: string
  mode: string
  status: string
  started_at: string
  ended_at: string | null
  total_duration_ms: number
  total_cost_usd: number
  total_tokens: number
  agent_chain: string[]
  error_count: number
  timeline: TimelineEntry[]
}

// Session blame
export interface SessionBlame {
  correlation_id: string
  total_errors: number
  error_agents: { agent: string; operation: string; error: string }[]
  slowest_agent: { agent: string; operation: string; duration_ms: number } | null
  agent_chain: string[]
}

// Sessions summary
export interface SessionsSummary {
  total_sessions: number
  completed: number
  errors: number
  error_rate: string
  avg_duration_ms: number
  avg_cost_usd: number
  avg_agents_per_session: number
}

// Hierarchy
export interface DirectorInfo {
  title: string
  departments: string[]
  scope: string
  capabilities: string[]
  existing_tools: string[]
}

export interface Specialist {
  code: string
  title: string
}

export interface HierarchyData {
  directors: Record<string, DirectorInfo>
  specialists: Record<string, Specialist[]>
}

// Merged agent (registry + health)
export interface MergedAgent extends AgentRegistryEntry {
  health?: AgentHealth
}
