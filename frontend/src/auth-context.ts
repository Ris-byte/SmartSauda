import { createContext, useContext } from 'react'
import type { User } from './types'

type Auth = { user: User | null; loading: boolean; error: string; signIn: (email: string, password: string) => Promise<void>; signOut: () => Promise<void>; clearSession: () => void; updateUser: (user: User) => void; refresh: () => Promise<void> }
export const AuthContext = createContext<Auth | null>(null)
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('AuthProvider missing'); return value }
