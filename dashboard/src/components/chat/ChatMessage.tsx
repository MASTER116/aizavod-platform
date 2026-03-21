import { formatDuration } from '../../utils/format'

export interface ChatMsg {
  id: string
  role: 'user' | 'agent' | 'system'
  text: string
  agent?: string
  avatar?: string
  color?: string
  title?: string
  duration_ms?: number
  qa_score?: number | null
  department?: string
  timestamp?: string
}

export function ChatMessage({ msg }: { msg: ChatMsg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] md:max-w-[60%] bg-[var(--color-zavod-gold)]/10 border border-[var(--color-zavod-gold)]/20 rounded-2xl rounded-br-md px-4 py-3">
          <div className="text-sm text-zinc-200 whitespace-pre-wrap">{msg.text}</div>
          {msg.timestamp && (
            <div className="text-[10px] text-zinc-500 mt-1 text-right">
              {new Date(msg.timestamp).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 mb-4">
      <div
        className="w-9 h-9 rounded-full flex items-center justify-center text-lg shrink-0 mt-1"
        style={{ background: (msg.color || '#71717a') + '22', border: `1px solid ${msg.color || '#71717a'}44` }}
      >
        {msg.avatar || '🤖'}
      </div>
      <div className="max-w-[80%] md:max-w-[70%]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium" style={{ color: msg.color || '#a1a1aa' }}>
            {msg.title || msg.agent || 'Agent'}
          </span>
          {msg.department && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500">{msg.department}</span>
          )}
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl rounded-tl-md px-4 py-3">
          <div className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">{msg.text}</div>
        </div>
        {(msg.duration_ms || msg.qa_score) && (
          <div className="flex gap-3 mt-1 text-[10px] text-zinc-500">
            {msg.duration_ms != null && <span>⏱ {formatDuration(msg.duration_ms)}</span>}
            {msg.qa_score != null && <span>📊 {typeof msg.qa_score === 'number' ? msg.qa_score.toFixed(1) : msg.qa_score}</span>}
          </div>
        )}
      </div>
    </div>
  )
}
