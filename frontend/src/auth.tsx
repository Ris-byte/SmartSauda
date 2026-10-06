import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api, ApiError, errorMessage, setCsrf } from './api'
import type { User } from './types'
import { AuthContext, useAuth } from './auth-context'
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null), [loading, setLoading] = useState(true), [error, setError] = useState('')
  async function loadUser() {
    try { const response = await api<{ user: User; csrf_token: string }>('/auth/me'); setUser(response.user); setCsrf(response.csrf_token); setError('') }
    catch (error) { setUser(null); if (!(error instanceof ApiError && error.status === 401)) setError(errorMessage(error)) }
    finally { setLoading(false) }
  }
  async function refresh() { setLoading(true); setError(''); await loadUser() }
  useEffect(() => {
    const controller = new AbortController()
    api<{ user: User; csrf_token: string }>('/auth/me', { signal: controller.signal }).then(response => {
      if (!controller.signal.aborted) { setUser(response.user); setCsrf(response.csrf_token) }
    }).catch(error => {
      if (!controller.signal.aborted && !(error instanceof ApiError && error.status === 401)) setError(errorMessage(error))
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    const expired = () => { setUser(null); setCsrf('') }
    window.addEventListener('smartsauda:session-expired', expired)
    return () => { controller.abort(); window.removeEventListener('smartsauda:session-expired', expired) }
  }, [])
  async function signIn(email: string, password: string) {
    const data = await api<{ user: User; csrf_token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
    setUser(data.user); setCsrf(data.csrf_token); setError('')
  }
  function clearSession() { setUser(null); setCsrf(''); setError('') }
  async function signOut() { await api('/auth/logout', { method: 'POST', body: '{}' }); clearSession() }
  return <AuthContext.Provider value={{ user, loading, error, signIn, signOut, clearSession, updateUser: setUser, refresh }}>{children}</AuthContext.Provider>
}
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading, error, refresh } = useAuth(); const location = useLocation()
  if (loading) return <div className="page-loading" role="status">Opening your garage…</div>
  if (error) return <div className="panel empty"><h1>Let’s reconnect.</h1><p>{error}</p><button className="button primary" onClick={() => void refresh()}>Try again</button></div>
  if (!user) return <Navigate to={`/signin?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  return children
}
