import { useActionState, useEffect, useState } from 'react'
import { api } from '../api/client'
import { ErrorNote } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import { storage } from '../utils/storage'

interface AuthActionState {
  error: unknown
  mode: 'in' | 'up'
}

export default function Login() {
  const { signIn, signUp } = useAuth()
  const [mode, setMode] = useState<'in' | 'up'>('in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [canRegister, setCanRegister] = useState<boolean | null>(null)

  const [actionState, formAction, isPending] = useActionState<AuthActionState, FormData>(
    async (_prev, formData) => {
      const submittedMode = formData.get('mode') === 'up' ? 'up' : 'in'
      const submittedEmail = String(formData.get('email') ?? '')
      const submittedPassword = String(formData.get('password') ?? '')
      try {
        if (submittedMode === 'in') {
          await signIn(submittedEmail, submittedPassword)
        } else {
          storage.set('prompt_new_user_tutorial', 'true')
          await signUp(submittedEmail, submittedPassword)
        }
        return { error: null, mode: submittedMode }
      } catch (err: unknown) {
        return { error: err, mode: submittedMode }
      }
    },
    { error: null, mode: 'in' },
  )

  useEffect(() => {
    let cancelled = false
    api
      .registrationStatus()
      .then((status) => {
        if (!cancelled) setCanRegister(status.open)
      })
      .catch(() => {
        if (!cancelled) setCanRegister(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    document.title = 'Sign in · Ars Memoriae'
  }, [])

  const visibleError = actionState.mode === mode ? actionState.error : null

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-2xl font-semibold text-slate-100">Ars Memoriae</h1>
      <p className="mt-2 text-sm text-slate-500">
        Active recall, FSRS scheduling, and AI-assisted reviews.
      </p>

      <form action={formAction} className="card mt-8 space-y-4">
        <input type="hidden" name="mode" value={mode} />
        <h2 className="text-sm font-semibold text-slate-200">
          {mode === 'in' ? 'Sign in' : 'Create your account'}
        </h2>
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
        </div>
        <div>
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            minLength={mode === 'up' ? 8 : undefined}
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'in' ? 'current-password' : 'new-password'}
            aria-describedby={mode === 'up' ? 'password-hint' : undefined}
          />
          {mode === 'up' && (
            <p id="password-hint" className="mt-1.5 text-xs text-slate-600">
              At least 8 characters.
            </p>
          )}
        </div>

        <ErrorNote error={visibleError} />

        <button type="submit" className="btn btn-primary w-full" disabled={isPending}>
          {isPending ? 'Working…' : mode === 'in' ? 'Sign in' : 'Create account'}
        </button>

        {mode === 'up' ? (
          <button
            type="button"
            className="w-full text-center text-xs text-slate-500 underline hover:text-slate-300"
            onClick={() => setMode('in')}
          >
            Sign in to an existing account
          </button>
        ) : canRegister ? (
          <button
            type="button"
            className="w-full text-center text-xs text-slate-500 underline hover:text-slate-300"
            onClick={() => setMode('up')}
          >
            Create an account
          </button>
        ) : canRegister === false ? (
          <p className="text-center text-xs text-slate-500">
            This installation already has its account, so sign-up is closed.
          </p>
        ) : null}
      </form>
    </div>
  )
}
