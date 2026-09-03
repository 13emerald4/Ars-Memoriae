import { lazy, Suspense } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { Spinner } from './components/ui'
import { useAuth } from './hooks/useAuth'

const CodeLab = lazy(() => import('./pages/CodeLab'))
const Decks = lazy(() => import('./pages/Decks'))
const FundamentalsStudio = lazy(() => import('./pages/FundamentalsStudio'))
const Login = lazy(() => import('./pages/Login'))
const Read = lazy(() => import('./pages/Read'))
const Review = lazy(() => import('./pages/Review'))
const Settings = lazy(() => import('./pages/Settings'))
const Stats = lazy(() => import('./pages/Stats'))
const Tree = lazy(() => import('./pages/Tree'))
const Tutorial = lazy(() => import('./pages/Tutorial'))

const NAV = [
  { to: '/tutorial', label: 'Start here' },
  { to: '/review', label: 'Review' },
  { to: '/code/fundamentals', label: '🛠 Pre-LeetCode' },
  { to: '/code', label: '⚡ Code Lab' },
  { to: '/tree', label: 'Tree' },
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

  if (!user) {
    return (
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center">
            <Spinner />
          </div>
        }
      >
        <Login />
      </Suspense>
    )
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-ink-line bg-ink/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <span className="text-sm font-semibold tracking-tight text-slate-100">Memorization</span>
          <nav className="flex flex-wrap gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
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

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Suspense
          fallback={
            <div className="flex min-h-[50vh] items-center justify-center">
              <Spinner />
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<Navigate to="/review" replace />} />
            <Route path="/tutorial" element={<Tutorial />} />
            <Route path="/review" element={<Review />} />
            <Route path="/code" element={<CodeLab />} />
            <Route path="/code/fundamentals" element={<FundamentalsStudio />} />
            <Route path="/tree" element={<Tree />} />
            <Route path="/read" element={<Read />} />
            <Route path="/read/:extractId" element={<Read />} />
            <Route path="/decks" element={<Decks />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/review" replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
