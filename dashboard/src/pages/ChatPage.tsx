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
          const errMsg: ChatMsg = {
            id: `msg_${Date.now()}_err`,
            role: 'system',
            text: `Error: ${e.data.message}`,
            timestamp: new Date().toISOString(),
          }
          setMessages(prev => [...prev, errMsg])
          break
      }
    })

    setSending(false)
    setTypingAgent(null)
  }, [selectedAgent, agents])

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile agent selector */}
        <AgentSidebar
          agents={agents}
          selectedAgent={selectedAgent}
          onSelect={setSelectedAgent}
        />

        {/* Header */}
        <div className="px-4 py-2 border-b border-zinc-800 flex items-center gap-2 bg-zinc-950/80">
          {currentAgent ? (
            <>
              <span className="text-lg">{currentAgent.avatar}</span>
              <div>
                <div className="text-sm font-medium" style={{ color: currentAgent.color }}>
                  {currentAgent.title}
                </div>
                <div className="text-[10px] text-zinc-500">{currentAgent.description}</div>
              </div>
            </>
          ) : (
            <>
              <span className="text-lg">🏭</span>
              <div>
                <div className="text-sm font-medium text-[var(--color-zavod-gold)]">Team Chat</div>
                <div className="text-[10px] text-zinc-500">CONDUCTOR автоматически выберет агента</div>
              </div>
            </>
          )}
        </div>

        {/* Messages */}
        <ChatMessages
          messages={messages}
          typingAgent={typingAgent}
          typingAvatar={typingMeta.avatar}
          typingColor={typingMeta.color}
        />

        {/* Quick actions */}
        <QuickActions
          actions={quickActions}
          onAction={handleSend}
          disabled={sending}
        />

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={sending}
          placeholder={currentAgent ? `Спросить ${currentAgent.title}...` : 'Введите вопрос или задачу...'}
        />
      </div>

      {/* Desktop agent sidebar */}
      <div className="hidden lg:block">
        <AgentSidebar
          agents={agents}
          selectedAgent={selectedAgent}
          onSelect={setSelectedAgent}
        />
      </div>
    </div>
  )
}
