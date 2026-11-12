import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, token, UNAUTHORIZED_EVENT } from '../api/client'
import type { User } from '../api/types'

interface AuthState {
  user: User | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signOut: () => void
  refresh: () => Promise<void>
  adoptToken: (accessToken: string) => void
}

const Ctx = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!token.get()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      let me = await api.me()
      // The server buckets "today" (daily caps, heatmap) by the user's local
      // study day; adopt the browser's zone the first time we see the user.
      if (!me.timezone) {
        const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
        if (zone) me = await api.updateMe({ timezone: zone }).catch(() => me)
      }
      setUser(me)
    } catch {
      token.clear()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.login(email, password)
      token.set(access_token)
      await refresh()
    },
    [refresh],
  )

  const signUp = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.register(email, password)
      token.set(access_token)
      await refresh()
    },
    [refresh],
  )

  const signOut = useCallback(() => {
    token.clear()
    setUser(null)
  }, [])

  // The API client clears the token and fires this when the server rejects
  // it (expired, revoked, password changed elsewhere). Dropping the user here
  // is what sends the app back to the sign-in screen.
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  /** Stores a replacement token (after a password change or revoking other
   *  sessions) without a round trip through the sign-in screen. */
  const adoptToken = useCallback((accessToken: string) => {
    token.set(accessToken)
  }, [])

  const value = useMemo(
    () => ({ user, loading, signIn, signUp, signOut, refresh, adoptToken }),
    [user, loading, signIn, signUp, signOut, refresh, adoptToken],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
