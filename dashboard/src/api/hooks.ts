import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  AgentHealth, AgentRegistryEntry, HealthSummary, AuditEntry,
  ObservabilitySummary, AgentStats, DailyCost,
  SessionItem, SessionReplay, SessionBlame, SessionsSummary,
  HierarchyData,
} from './types'

// Agent Health (refetch every 15s)
export const useAgentHealth = () =>
  useQuery<AgentHealth[]>({ queryKey: ['agents', 'health'], queryFn: api.agentsHealth, refetchInterval: 15000 })

export const useAgentSummary = () =>
  useQuery<HealthSummary>({ queryKey: ['agents', 'summary'], queryFn: api.agentsSummary, refetchInterval: 15000 })

export const useAgentAudit = (limit = 50) =>
  useQuery<AuditEntry[]>({ queryKey: ['agents', 'audit', limit], queryFn: () => api.agentsAudit(limit) })

// Registry (static, long cache)
export const useAgentRegistry = () =>
  useQuery<AgentRegistryEntry[]>({ queryKey: ['agents', 'registry'], queryFn: api.agentsRegistry, staleTime: Infinity })

// Hierarchy (static)
export const useHierarchy = () =>
  useQuery<HierarchyData>({ queryKey: ['hierarchy'], queryFn: api.hierarchy, staleTime: Infinity })

// Mutations
export const useKillAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, reason }: { name: string; reason: string }) => api.agentKill(name, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export const useReviveAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.agentRevive(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export const useSuspendAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, reason }: { name: string; reason: string }) => api.agentSuspend(name, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

// Observability
export const useObservabilitySummary = () =>
  useQuery<ObservabilitySummary>({ queryKey: ['observability', 'summary'], queryFn: api.observabilitySummary, refetchInterval: 30000 })

export const useAgentStats = () =>
  useQuery<AgentStats[]>({ queryKey: ['observability', 'agents'], queryFn: api.observabilityAgents, refetchInterval: 30000 })

export const useDailyCosts = (from: string, to: string) =>
  useQuery<DailyCost[]>({ queryKey: ['observability', 'daily-costs', from, to], queryFn: () => api.dailyCosts(from, to) })

// Sessions
export const useRecentSessions = (limit = 20) =>
  useQuery<SessionItem[]>({ queryKey: ['sessions', 'recent', limit], queryFn: () => api.sessionsRecent(limit), refetchInterval: 15000 })

export const useSessionsSummary = () =>
  useQuery<SessionsSummary>({ queryKey: ['sessions', 'summary'], queryFn: api.sessionsSummary, refetchInterval: 30000 })

export const useSessionReplay = (id: string | null) =>
  useQuery<SessionReplay>({
    queryKey: ['sessions', 'replay', id],
    queryFn: () => api.sessionReplay(id!),
    enabled: !!id,
  })

export const useSessionBlame = (id: string | null) =>
  useQuery<SessionBlame>({
    queryKey: ['sessions', 'blame', id],
    queryFn: () => api.sessionBlame(id!),
    enabled: !!id,
  })
