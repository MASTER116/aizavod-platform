import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChatMessages } from '../components/chat/ChatMessages'
import { ChatInput } from '../components/chat/ChatInput'
import { QuickActions } from '../components/chat/QuickActions'
import { AgentSidebar, type AgentPersona } from '../components/chat/AgentSidebar'
import { streamChat } from '../api/chatStream'
import { api } from '../api/client'
import type { ChatMsg } from '../components/chat/ChatMessage'

export function ChatPage() {
  const { agentName } = useParams<{ agentName?: string }>()
  const [selectedAgent, setSelectedAgent] = useState<string | null>(agentName || null)
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [sending, setSending] = useState(false)
  const [typingAgent, setTypingAgent] = useState<string | null>(null)
  const [typingMeta, setTypingMeta] = useState<{ avatar?: string; color?: string }>({})

  const { data: agents = [] } = useQuery<AgentPersona[]>({
    queryKey: ['chat', 'agents'],
    queryFn: () => api.request('/admin/api/dashboard/chat/agents'),
    staleTime: Infinity,
  })

  // Load history on mount
  useEffect(() => {
    api.request<ChatMsg[]>('/admin/api/dashboard/chat/history?limit=50')
      .then(history => { if (history?.length) setMessages(history) })
      .catch(() => {})
  }, [])

  // Sync URL param
  useEffect(() => {
    if (agentName) setSelectedAgent(agentName)
  }, [agentName])

  const currentAgent = agents.find(a => a.name === selectedAgent)
  const quickActions = currentAgent?.quick_actions || [
    'Найди гранты', 'Анализ рынка', 'Юридическая консультация', 'Идеи заработка'
  ]

  const handleSend = useCallback(async (text: string) => {
    const userMsg: ChatMsg = {
      id: `msg_${Date.now()}`,
      role: 'user',
      text,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setSending(true)
    setTypingAgent('CONDUCTOR')
    setTypingMeta({ avatar: '🏭', color: '#d4a017' })

    let agentResponse: Partial<ChatMsg> = {}

    await streamChat(text, selectedAgent || undefined, (e) => {
      switch (e.event) {
        case 'thinking':
          setTypingAgent('CONDUCTOR')
          setTypingMeta({ avatar: '🏭', color: '#d4a017' })
          break

        case 'routed': {
          const name = e.data.agent as string
          const persona = agents.find(a => a.name === name)
          setTypingAgent(persona?.title || name)
          setTypingMeta({ avatar: persona?.avatar || '🤖', color: persona?.color || '#71717a' })
          agentResponse = {
            agent: name,
            avatar: persona?.avatar || '🤖',
            color: persona?.color || '#71717a',
            title: persona?.title || name,
            department: e.data.department as string,
          }
          break
        }

        case 'chunk': {
          const agentMsg: ChatMsg = {
            id: `msg_${Date.now()}_agent`,
            role: 'agent',
            text: e.data.text as string,
            ...agentResponse,
            timestamp: new Date().toISOString(),
          }
          setMessages(prev => [...prev, agentMsg])
          setTypingAgent(null)
          break
        }

        case 'secondary': {
          const secPersona = agents.find(a => a.name === e.data.agent)
          const secMsg: ChatMsg = {
            id: `msg_${Date.now()}_sec_${e.data.agent}`,
            role: 'agent',
            text: e.data.text as string,
            agent: e.data.agent as string,
            avatar: secPersona?.avatar || '🤖',
            color: secPersona?.color || '#71717a',
            title: secPersona?.title || (e.data.agent as string),
            timestamp: new Date().toISOString(),
          }
          setMessages(prev => [...prev, secMsg])
          break
        }

        case 'done':
          setMessages(prev => {
            const updated = [...prev]
            const last = updated.findLast(m => m.role === 'agent')
            if (last) {
              last.duration_ms = e.data.duration_ms as number
              last.qa_score = e.data.qa_score as number | null
            }
            return updated
          })
          setTypingAgent(null)
          setSending(false)
          break

        case 'error':
          setTypingAgent(null)
          setSending(false)
          setMessages(prev => [...prev, {
            id: `msg_${Date.now()}_err`,
            role: 'system' as const,
            text: `Error: ${e.data.message}`,
            timestamp: new Date().toISOString(),
          }])
          break
      }
    })

    setSending(false)
    setTypingAgent(null)
  }, [selectedAgent, agents])

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile agent selector (horizontal scroll) */}
        <div className="lg:hidden">
          <AgentSidebar agents={agents} selectedAgent={selectedAgent} onSelect={setSelectedAgent} />
        </div>

        {/* Chat header */}
        <div className="px-4 py-2.5 border-b border-zinc-800 flex items-center gap-3 bg-zinc-950/80 shrink-0">
          {currentAgent ? (
            <>
              <span className="text-xl">{currentAgent.avatar}</span>
              <div>
                <div className="text-sm font-medium" style={{ color: currentAgent.color }}>
                  {currentAgent.title}
                </div>
                <div className="text-[10px] text-zinc-500">{currentAgent.description}</div>
              </div>
            </>
          ) : (
            <>
              <span className="text-xl">🏭</span>
              <div>
                <div className="text-sm font-medium text-[var(--color-zavod-gold)]">Team Chat</div>
                <div className="text-[10px] text-zinc-500">CONDUCTOR автоматически выберет нужного агента</div>
              </div>
            </>
          )}
        </div>

        {/* Messages area */}
        <ChatMessages
          messages={messages}
          typingAgent={typingAgent}
          typingAvatar={typingMeta.avatar}
          typingColor={typingMeta.color}
        />

        {/* Quick actions */}
        <QuickActions actions={quickActions} onAction={handleSend} disabled={sending} />

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={sending}
          placeholder={currentAgent ? `Спросить ${currentAgent.title}...` : 'Введите вопрос или задачу...'}
        />
      </div>

      {/* Desktop agent sidebar (right side) */}
      <div className="hidden lg:flex flex-col w-56 border-l border-zinc-800 bg-zinc-950 overflow-y-auto shrink-0">
        <div className="p-3 border-b border-zinc-800 text-xs font-medium text-zinc-400">
          Agents ({agents.length})
        </div>
        <button
          className={`w-full text-left px-3 py-2.5 text-xs transition-colors ${
            !selectedAgent ? 'bg-zinc-900 text-[var(--color-zavod-gold)]' : 'text-zinc-400 hover:bg-zinc-900'
          }`}
          onClick={() => setSelectedAgent(null)}
        >
          🏭 Team Chat (auto-route)
        </button>
        {agents.map(a => (
          <button
            key={a.name}
            className={`w-full text-left px-3 py-2 flex items-center gap-2 transition-colors ${
              selectedAgent === a.name ? 'bg-zinc-900 border-l-2' : 'text-zinc-400 hover:bg-zinc-900/50'
            }`}
            style={selectedAgent === a.name ? { borderLeftColor: a.color, color: a.color } : {}}
            onClick={() => setSelectedAgent(a.name)}
          >
            <span className="text-sm">{a.avatar}</span>
            <div className="min-w-0">
              <div className="text-xs truncate">{a.title}</div>
              <div className="text-[10px] text-zinc-600 truncate">{a.department}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
