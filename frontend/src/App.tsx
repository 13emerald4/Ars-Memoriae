import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Spinner } from './components/ui'
import { useAuth } from './hooks/useAuth'
import InteractiveTutorialModal from './components/InteractiveTutorialModal'

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
  { to: '/code/fundamentals', label: 'Pre-LeetCode' },
  { to: '/code', label: 'Code Lab' },
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
      title="Lexicon"
      className="flex items-center gap-1.5 rounded-lg border border-sky-500/40 bg-sky-500/10 px-2.5 py-1 text-xs font-semibold text-sky-200 hover:bg-sky-500/20 hover:border-sky-400 transition-colors"
    >
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
import {
  ThemeProvider,
  useTheme,
  THEME_REGISTRY,
  CognitiveTheme,
} from './components/ThemeContext'

function ThemeNavButton() {
  const {
    themeMode,
    setThemeMode,
    fixedTheme,
    setFixedTheme,
    activeThemeMeta,
    enableOledBlack,
    setEnableOledBlack,
  } = useTheme()
  const [open, setOpen] = useState(false)

  const navLabel =
    themeMode === 'dynamic'
      ? 'Adaptive'
      : activeThemeMeta.id === 'dark'
        ? 'Dark'
        : activeThemeMeta.label.split(' ')[0]

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title={`Theme: ${activeThemeMeta.label}`}
        className="flex items-center gap-1.5 rounded-lg border border-ink-line bg-ink-soft px-2 py-1 text-xs font-semibold text-slate-300 hover:border-slate-500 hover:text-slate-100 transition-colors cursor-pointer"
      >
        <span className="text-[11px]">{navLabel}</span>
        <span
          className="w-2 h-2 rounded-full border border-white/20 shrink-0"
          style={{ backgroundColor: activeThemeMeta.primaryColor }}
        />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-80 z-50 rounded-xl border border-ink-line bg-ink-soft p-3 shadow-2xl backdrop-blur">
            <div className="flex items-center justify-between pb-2 border-b border-ink-line text-xs">
              <span className="font-bold text-slate-200 flex items-center gap-1.5">
                <span>Theme</span>
              </span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm cursor-pointer"
              >
                &times;
              </button>
            </div>

            {/* Mode Switcher */}
            <div className="grid grid-cols-2 gap-1.5 my-2.5 p-1 rounded-lg bg-ink border border-ink-line text-xs font-medium">
              <button
                type="button"
                onClick={() => setThemeMode('dynamic')}
                className={`py-1 px-2 rounded flex items-center justify-center gap-1 transition cursor-pointer ${
                  themeMode === 'dynamic'
                    ? 'bg-sky-600/40 text-sky-200 border border-sky-500/60 font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Adaptive palette"
              >
                <span>Adaptive</span>
              </button>
              <button
                type="button"
                onClick={() => setThemeMode('fixed')}
                className={`py-1 px-2 rounded flex items-center justify-center gap-1 transition cursor-pointer ${
                  themeMode === 'fixed'
                    ? 'bg-sky-600/40 text-sky-200 border border-sky-500/60 font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Fixed palette"
              >
                <span>Fixed</span>
              </button>
            </div>

            {/* OLED / Pure Black Toggle */}
            <div className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-ink border border-ink-line mb-2.5 text-xs">
              <span className="flex items-center gap-1.5 text-slate-300 font-medium text-[11px]">
                <span>OLED Pure Black</span>
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={enableOledBlack}
                onClick={() => setEnableOledBlack(!enableOledBlack)}
                className={`w-7 h-4 rounded-full transition-colors relative cursor-pointer ${
                  enableOledBlack ? 'bg-sky-500' : 'bg-slate-700'
                }`}
                title="Force true pitch black (#000000) canvas"
              >
                <span
                  className={`w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform ${
                    enableOledBlack ? 'left-3.5' : 'left-0.5'
                  }`}
                />
              </button>
            </div>

            {/* Palette Options */}
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 font-semibold">
              {themeMode === 'dynamic' ? 'Current Palette (or click to lock):' : 'Select Fixed Palette:'}
            </p>
            <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
              {(Object.keys(THEME_REGISTRY) as CognitiveTheme[]).map((id) => {
                const meta = THEME_REGISTRY[id]
                const isSelected = themeMode === 'fixed' ? fixedTheme === id : activeThemeMeta.id === id
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      if (themeMode === 'dynamic') {
                        setThemeMode('fixed')
                      }
                      setFixedTheme(id)
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between transition border cursor-pointer ${
                      isSelected
                        ? 'border-sky-500/50 bg-sky-500/15 text-white font-medium shadow-sm'
                        : 'border-transparent hover:bg-slate-800/60 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate pr-2">
                      <div className="truncate">
                        <span className="block truncate font-medium">{meta.label}</span>
                        <span className="block truncate text-[10px] text-slate-400">{meta.subtitle}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <span
                        className="w-3 h-3 rounded-full border border-white/20 shadow-sm"
                        style={{ backgroundColor: meta.primaryColor }}
                        title={`Primary: ${meta.primaryColor}`}
                      />
                      <span
                        className="w-3 h-3 rounded-full border border-white/20 shadow-sm"
                        style={{ backgroundColor: meta.secondaryColor }}
                        title={`Secondary: ${meta.secondaryColor}`}
                      />
                    </div>
                  </button>
                )
              })}
            </div>

            <div className="mt-2.5 pt-2 border-t border-ink-line text-[11px] text-slate-400 flex justify-between items-center">
              <span>{activeThemeMeta.subtitle}</span>
              <NavLink
                to="/settings"
                onClick={() => setOpen(false)}
                className="text-sky-400 hover:text-sky-300 underline font-medium"
              >
                Settings →
              </NavLink>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function AppLayout() {
  const { user } = useAuth()
  const location = useLocation()
  const isWide = location.pathname.startsWith('/code') || location.pathname.startsWith('/review')
  const { isFullscreen, isZenMode } = useFullscreen()
  const [headerHovered, setHeaderHovered] = useState(false)
  const [showTutorialPrompt, setShowTutorialPrompt] = useState(false)

  useEffect(() => {
    if (user && !user.tutorial_completed) {
      const isNewSignup = localStorage.getItem('prompt_new_user_tutorial') === 'true'
      const isDismissed = localStorage.getItem('tutorial_prompt_dismissed') === 'true'
      if (isNewSignup || !isDismissed) {
        setShowTutorialPrompt(true)
      }
    }
  }, [user])

  const hideHeader = isZenMode && !headerHovered

  const visibleNav = useMemo(() => {
    return NAV.filter((item) => {
      if (item.to === '/code/fundamentals' && !user?.show_pre_leetcode) return false
      if (item.to === '/code' && !user?.show_code_lab) return false
      return true
    })
  }, [user?.show_pre_leetcode, user?.show_code_lab])

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
              {visibleNav.map((item) => (
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
            <ThemeNavButton />
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

      <InteractiveTutorialModal
        isOpen={showTutorialPrompt}
        onClose={() => setShowTutorialPrompt(false)}
        initialMode="prompt"
      />
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
    <ThemeProvider>
      <FullscreenProvider>
        <LexiconProvider>
          <AppLayout />
        </LexiconProvider>
      </FullscreenProvider>
    </ThemeProvider>
  )
}
