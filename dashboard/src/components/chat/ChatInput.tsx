import { useState, useRef, useEffect } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, placeholder }: Props) {
  const [text, setText] = useState('')
  const [listening, setListening] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const toggleVoice = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) return

    if (listening && recognitionRef.current) {
      recognitionRef.current.stop()
      setListening(false)
      return
    }

    const recognition = new SR()
    recognition.lang = 'ru-RU'
    recognition.continuous = false
    recognition.interimResults = false
    recognition.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript
      setText(prev => (prev ? prev + ' ' + transcript : transcript))
      setListening(false)
    }
    recognition.onerror = () => setListening(false)
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }

  const hasSpeechAPI = typeof window !== 'undefined' && ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)

  return (
    <div className="border-t border-zinc-800 p-3 bg-zinc-950">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        {hasSpeechAPI && (
          <button
            onClick={toggleVoice}
            className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
              listening
                ? 'bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse'
                : 'bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-zinc-700'
            }`}
            title={listening ? 'Остановить запись' : 'Голосовой ввод'}
          >
            🎤
          </button>
        )}
        <textarea
          ref={inputRef}
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 resize-none focus:outline-none focus:border-[var(--color-zavod-gold)] min-h-[42px] max-h-[120px]"
          placeholder={placeholder || 'Введите сообщение...'}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          className="shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-[var(--color-zavod-gold)] text-black disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
        >
          ➤
        </button>
      </div>
    </div>
  )
}
