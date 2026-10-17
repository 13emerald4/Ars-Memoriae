import { useState } from 'react'
import { ErrorNote } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const { signIn, signUp } = useAuth()
  const [mode, setMode] = useState<'in' | 'up'>('in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (mode === 'in') {
        await signIn(email, password)
      } else {
        localStorage.setItem('prompt_new_user_tutorial', 'true')
        await signUp(email, password)
      }
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-2xl font-semibold text-slate-100">Memorization</h1>
      <p className="mt-2 text-sm text-slate-500">
        Active recall, FSRS scheduling, and AI-assisted reviews.
      </p>

      <form onSubmit={submit} className="card mt-8 space-y-4">
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
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
            type="password"
            required
            minLength={8}
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'in' ? 'current-password' : 'new-password'}
          />
          {mode === 'up' && (
            <p className="mt-1.5 text-xs text-slate-600">At least 8 characters.</p>
          )}
        </div>

        <ErrorNote error={error} />

        <button type="submit" className="btn btn-primary w-full" disabled={busy}>
          {busy ? 'Working…' : mode === 'in' ? 'Sign in' : 'Create account'}
        </button>

        <button
          type="button"
          className="w-full text-center text-xs text-slate-500 hover:text-slate-300"
          onClick={() => {
            setMode(mode === 'in' ? 'up' : 'in')
            setError(null)
          }}
        >
          {mode === 'in' ? 'Create an account' : 'Sign in to existing account'}
        </button>
      </form>
    </div>
  )
}
