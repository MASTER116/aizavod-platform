export interface ChatEvent {
  event: 'thinking' | 'routed' | 'chunk' | 'secondary' | 'done' | 'error'
  data: Record<string, unknown>
}

export async function streamChat(
  message: string,
  agent: string | undefined,
  onEvent: (e: ChatEvent) => void,
): Promise<void> {
  const token = localStorage.getItem('zavod_token')

  const res = await fetch('/admin/api/dashboard/chat/send', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, agent }),
  })

  if (!res.ok || !res.body) {
    onEvent({ event: 'error', data: { message: `HTTP ${res.status}` } })
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let currentEvent = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ') && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6))
          onEvent({ event: currentEvent as ChatEvent['event'], data })
        } catch { /* skip bad json */ }
        currentEvent = ''
      }
    }
  }
}
