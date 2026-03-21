import { useEffect, useRef } from 'react'
import { ChatMessage, type ChatMsg } from './ChatMessage'

interface Props {
  messages: ChatMsg[]
  typingAgent?: string | null
  typingAvatar?: string
  typingColor?: string
}

export function ChatMessages({ messages, typingAgent, typingAvatar, typingColor }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, typingAgent])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <span className="text-4xl mb-4">🏭</span>
          <h2 className="text-lg font-semibold text-zinc-300 mb-2">ZAVOD-II Team Chat</h2>
          <p className="text-sm text-zinc-500 max-w-md">
            Напишите вопрос или задачу — CONDUCTOR направит к нужному агенту.
            Или выберите агента справа для прямого общения.
          </p>
        </div>
      )}
      {messages.map(msg => (
        <ChatMessage key={msg.id} msg={msg} />
      ))}
      {typingAgent && (
        <div className="flex gap-3 mb-4">
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center text-lg shrink-0"
            style={{ background: (typingColor || '#71717a') + '22', border: `1px solid ${typingColor || '#71717a'}44` }}
          >
            {typingAvatar || '🤖'}
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl rounded-tl-md px-4 py-3">
            <div className="flex items-center gap-1">
              <span className="text-xs" style={{ color: typingColor || '#a1a1aa' }}>{typingAgent}</span>
              <span className="text-xs text-zinc-500 ml-1">думает</span>
              <span className="inline-flex gap-0.5 ml-1">
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
