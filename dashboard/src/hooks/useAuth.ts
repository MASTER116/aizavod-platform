import { useState, useCallback } from 'react'

export function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem('zavod_token'))

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch('/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) throw new Error('Invalid credentials')
    const data = await res.json()
    localStorage.setItem('zavod_token', data.access_token)
    setToken(data.access_token)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('zavod_token')
    setToken(null)
  }, [])

  return { token, isAuthenticated: !!token, login, logout }
}
