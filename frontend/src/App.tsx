import { lazy, Suspense, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
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

import { LexiconProvider, useLexicon } from './components/LexiconContext'

function LexiconNavButton() {
  const { openLexicon } = useLexicon()
  return (
    <button
      type="button"
      data-lexicon-trigger="true"
      onClick={() => openLexicon('binary approximations')}
      title="Concordance & Lexicon: Look up definitions and related technical concepts"
      className="flex items-center gap-1.5 rounded-lg border border-sky-500/40 bg-sky-500/10 px-2.5 py-1 text-xs font-semibold text-sky-200 hover:bg-sky-500/20 hover:border-sky-400 transition-colors"
    >
      <span>📖</span>
      <span className="hidden sm:inline">Lexicon</span>
    </button>
  )
}

import {
  FullscreenProvider,
  FullscreenButton,
  FullscreenHud,
  useFullscreen,
} from './components/FullscreenContext'

function AppLayout() {
  const location = useLocation()
  const isWide = location.pathname.startsWith('/code') || location.pathname.startsWith('/review')
  const { isFullscreen, isZenMode } = useFullscreen()
  const [headerHovered, setHeaderHovered] = useState(false)

  const hideHeader = isZenMode && !headerHovered

  return (
    <div className={`min-h-screen ${isFullscreen ? 'bg-[#090d16]' : ''}`}>
      {/* Invisible Hover Sensor at the top edge to reveal header when in Zen Mode */}
      {isZenMode && (
        <div
          onMouseEnter={() => setHeaderHovered(true)}
          className="fixed top-0 left-0 right-0 h-3 z-30 pointer-events-auto"
        />
      )}

      <header
        onMouseEnter={() => setHeaderHovered(true)}
        onMouseLeave={() => setHeaderHovered(false)}
        className={`sticky top-0 z-20 border-b border-ink-line bg-ink/90 backdrop-blur transition-all duration-200 ${
          hideHeader
            ? '-translate-y-full opacity-0 pointer-events-none'
            : 'translate-y-0 opacity-100 pointer-events-auto'
        }`}
      >
        <div
          className={
            isWide
              ? 'mx-auto flex w-full max-w-[1850px] items-center justify-between gap-4 px-4 py-2.5'
              : 'mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3'
          }
        >
          <span className="text-sm font-semibold tracking-tight text-slate-100">Ars Memoriae</span>
          <div className="flex items-center gap-2.5">
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
            <LexiconNavButton />
            <FullscreenButton />
          </div>
        </div>
      </header>

      {/* Floating HUD pill when in Fullscreen or Zen mode */}
      <FullscreenHud />

      <main
        className={
          isWide
            ? `mx-auto w-full max-w-[1850px] px-4 ${isZenMode ? 'py-2' : 'py-4'}`
            : `mx-auto max-w-6xl px-6 ${isZenMode ? 'py-4' : 'py-8'}`
        }
      >
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
    <FullscreenProvider>
      <LexiconProvider>
        <AppLayout />
      </LexiconProvider>
    </FullscreenProvider>
  )
}
