import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { Spinner } from './components/ui'
import { useAuth } from './hooks/useAuth'
import Decks from './pages/Decks'
import Login from './pages/Login'
import Read from './pages/Read'
import Review from './pages/Review'
import Settings from './pages/Settings'
import Stats from './pages/Stats'

const NAV = [
  { to: '/review', label: 'Review' },
  { to: '/read', label: 'Read' },
  { to: '/decks', label: 'Decks' },
  { to: '/stats', label: 'Stats' },
  { to: '/settings', label: 'Settings' },
]

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  if (!user) return <Login />

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-ink-line bg-ink/90 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-6 py-3">
          <span className="text-sm font-semibold tracking-tight text-slate-100">Memorization</span>
          <nav className="flex gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm transition ${
                    isActive
                      ? 'bg-sky-500/15 text-sky-200'
                      : 'text-slate-400 hover:bg-ink-soft hover:text-slate-200'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/review" replace />} />
          <Route path="/review" element={<Review />} />
          <Route path="/read" element={<Read />} />
          <Route path="/read/:extractId" element={<Read />} />
          <Route path="/decks" element={<Decks />} />
          <Route path="/stats" element={<Stats />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/review" replace />} />
        </Routes>
      </main>
    </div>
  )
}
