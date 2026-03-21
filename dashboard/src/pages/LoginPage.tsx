import { useState } from 'react'

export function LoginPage({ onLogin }: { onLogin: (u: string, p: string) => Promise<void> }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onLogin(username, password)
    } catch {
      setError('Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-zavod-bg)]">
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-xl p-8">
        <div className="text-center mb-8">
          <span className="text-3xl">🏭</span>
          <h1 className="text-lg font-bold mt-2 bg-gradient-to-r from-[var(--color-zavod-gold)] to-[var(--color-zavod-gold-light)] bg-clip-text text-transparent">
            ZAVOD-II Dashboard
          </h1>
        </div>
        {error && <div className="text-red-400 text-sm text-center mb-4">{error}</div>}
        <input
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-sm mb-3 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-[var(--color-zavod-gold)]"
          placeholder="Username"
          value={username}
          onChange={e => setUsername(e.target.value)}
        />
        <input
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-sm mb-6 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-[var(--color-zavod-gold)]"
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-lg text-sm font-medium text-black bg-gradient-to-r from-[var(--color-zavod-gold)] to-[var(--color-zavod-gold-light)] hover:opacity-90 disabled:opacity-50"
        >
          {loading ? '...' : 'Login'}
        </button>
      </form>
    </div>
  )
}
