import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Spinner } from './components/ui'
import { DialogHost } from './components/dialogs'
import { NativePopover } from './components/NativePopover'
import { useAuth } from './hooks/useAuth'
import { createSyncSocket } from './api/client'
import { WorkspaceProvider, useWorkspace } from './components/WorkspaceContext'
import { WorkspaceCustomizerDrawer } from './components/WorkspaceCustomizerDrawer'
import { CommandPalette } from './components/CommandPalette'
import { ALL_NAV_ROUTES } from './utils/workspaceModules'

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

import { LexiconProvider, useLexicon } from './components/LexiconContext'

function LexiconNavButton() {
  const { openLexicon } = useLexicon()
  return (
    <button
      type="button"
      data-lexicon-trigger="true"
      onClick={() => openLexicon()}
      title="Open the lexicon"
      className="flex items-center gap-1.5 rounded-lg border border-sky-500/40 bg-sky-500/10 px-2.5 py-1 text-xs font-semibold text-sky-200 hover:bg-sky-500/20 hover:border-sky-400 transition-colors"
    >
      {/* The label used to be hidden below 640px with nothing in its place,
          which left an empty, unlabeled pill on phones. */}
      <span>Lexicon</span>
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
    enableGreyscaleFriendly,
    setEnableGreyscaleFriendly,
  } = useTheme()

  const navLabel =
    themeMode === 'dynamic'
      ? 'Adaptive'
      : activeThemeMeta.id === 'dark'
        ? 'Dark'
        : activeThemeMeta.label.split(' ')[0]

  return (
    <NativePopover
      align="right"
      role="dialog"
      ariaLabel="Theme"
      trigger={(props) => (
        <button
          {...props}
          type="button"
          title={`Theme: ${activeThemeMeta.label}`}
          aria-haspopup="dialog"
          className="flex items-center gap-1.5 rounded-lg border border-ink-line bg-ink-soft px-2 py-1 text-xs font-semibold text-slate-300 hover:border-slate-500 hover:text-slate-100 transition-colors cursor-pointer"
        >
          <span className="text-[0.6875rem]">{navLabel}</span>
          <span
            className="w-2 h-2 rounded-full border border-white/20 shrink-0"
            style={{ backgroundColor: activeThemeMeta.primaryColor }}
          />
        </button>
      )}
    >
      {({ close }) => (
        <div className="w-80 max-w-[calc(100vw-1.5rem)] rounded-xl border border-ink-line bg-ink-soft p-3 shadow-2xl outline-none">
          <div className="flex items-center justify-between pb-2 border-b border-ink-line text-xs">
            <span className="font-bold text-slate-200 flex items-center gap-1.5">
              <span>Theme</span>
            </span>
            <button
              type="button"
              onClick={close}
              aria-label="Close theme menu"
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
          <div className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-ink border border-ink-line mb-2 text-xs">
            <span className="flex items-center gap-1.5 text-slate-300 font-medium text-[0.6875rem]">
              <span>OLED Pure Black</span>
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={enableOledBlack}
              aria-label="OLED pure black"
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

          {/* Greyscale Friendly Toggle */}
          <div className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-ink border border-ink-line mb-2.5 text-xs">
            <span className="flex items-center gap-1.5 text-slate-300 font-medium text-[0.6875rem]">
              <span>Greyscale Mode</span>
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={enableGreyscaleFriendly}
              aria-label="Greyscale mode"
              onClick={() => setEnableGreyscaleFriendly(!enableGreyscaleFriendly)}
              className={`w-7 h-4 rounded-full transition-colors relative cursor-pointer ${
                enableGreyscaleFriendly ? 'bg-white' : 'bg-slate-700'
              }`}
              title="Optimize UI contrast, patterns, and token diffs for greyscale displays"
            >
              <span
                className={`w-3 h-3 rounded-full absolute top-0.5 transition-transform ${
                  enableGreyscaleFriendly ? 'left-3.5 bg-black' : 'left-0.5 bg-white'
                }`}
              />
            </button>
          </div>

          {/* Palette Options */}
          <p className="text-[0.625rem] text-slate-500 uppercase tracking-wider mb-1 font-semibold">
            {themeMode === 'dynamic' ? 'Current Palette (or click to lock):' : 'Select Fixed Palette:'}
          </p>
          <div className="space-y-1 max-h-56 overflow-y-auto pr-1 scroll-stable">
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
                      <span className="block truncate text-[0.625rem] text-slate-400">{meta.subtitle}</span>
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

          <div className="mt-2.5 pt-2 border-t border-ink-line text-[0.6875rem] text-slate-400 flex justify-between items-center">
            <span>{activeThemeMeta.subtitle}</span>
            <NavLink
              to="/settings"
              onClick={close}
              className="text-sky-400 hover:text-sky-300 underline font-medium"
            >
              Settings →
            </NavLink>
          </div>
        </div>
      )}
    </NativePopover>
  )
}

function MoreNavMenu({
  unpinnedRoutes,
  onOpenCustomizer,
  userEmail,
  onSignOut,
}: {
  unpinnedRoutes: typeof ALL_NAV_ROUTES
  onOpenCustomizer: () => void
  userEmail?: string
  onSignOut: () => void
}) {
  const location = useLocation()

  const hasActiveUnpinned = unpinnedRoutes.some(
    (r) => location.pathname === r.to || location.pathname.startsWith(`${r.to}/`),
  )

  return (
    <NativePopover
      align="left"
      role="menu"
      ariaLabel="Additional workspaces"
      closeSignal={location.pathname}
      trigger={(props) => (
        <button
          {...props}
          type="button"
          aria-haspopup="menu"
          className={`flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium whitespace-nowrap shrink-0 transition-colors cursor-pointer ${
            hasActiveUnpinned
              ? 'bg-sky-500/15 text-sky-200'
              : 'text-slate-400 hover:bg-ink-soft hover:text-slate-200'
          }`}
        >
          <span>More</span>
          <svg
            className={`h-3 w-3 transition-transform ${props['aria-expanded'] ? 'rotate-180' : ''}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      )}
    >
      {({ close }) => (
        <div className="w-60 rounded-xl border border-ink-line bg-ink-soft p-1.5 shadow-2xl outline-none">
          {unpinnedRoutes.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/code'}
              role="menuitem"
              onClick={close}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 transition-colors ${
                  isActive
                    ? 'bg-sky-500/15 text-sky-100'
                    : 'text-slate-200 hover:bg-ink hover:text-white'
                }`
              }
            >
              <span className="block text-xs font-medium">{item.label}</span>
              <span className="block text-[0.6875rem] text-slate-400">{item.description}</span>
            </NavLink>
          ))}
          <div className="my-1.5 border-t border-ink-line" />
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              close()
              onOpenCustomizer()
            }}
            className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs text-sky-300 hover:bg-ink transition-colors cursor-pointer"
          >
            <span>Customize navigation…</span>
          </button>
          <div className="mt-1 flex items-center justify-between border-t border-ink-line px-3 pt-2 pb-1 text-[0.6875rem] text-slate-400">
            <span className="truncate pr-2">{userEmail}</span>
            <button
              type="button"
              onClick={() => {
                close()
                onSignOut()
              }}
              className="shrink-0 text-rose-300 hover:text-rose-200 cursor-pointer"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </NativePopover>
  )
}

function AppLayout() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const isWide = location.pathname.startsWith('/code') || location.pathname.startsWith('/review')
  const { isFullscreen, isZenMode } = useFullscreen()
  const { config, setCustomizerOpen, setCommandPaletteOpen } = useWorkspace()
  const [headerHovered, setHeaderHovered] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (!user) return
    const cleanup = createSyncSocket((event) => {
      window.dispatchEvent(new CustomEvent('ars:sync', { detail: event }))
    })
    return cleanup
  }, [user])

  const hideHeader = isZenMode && !headerHovered

  const availableNav = useMemo(() => {
    return ALL_NAV_ROUTES.filter((item) => {
      if (item.to === '/code/fundamentals' && !user?.show_pre_leetcode) return false
      if (item.to === '/code' && !user?.show_code_lab) return false
      return true
    })
  }, [user?.show_pre_leetcode, user?.show_code_lab])

  const pinnedNav = useMemo(
    () => availableNav.filter((item) => config.pinnedNavRoutes.includes(item.to)),
    [availableNav, config.pinnedNavRoutes],
  )

  const unpinnedNav = useMemo(
    () => availableNav.filter((item) => !config.pinnedNavRoutes.includes(item.to)),
    [availableNav, config.pinnedNavRoutes],
  )

  const pageTitle = useMemo(() => {
    const match = [...ALL_NAV_ROUTES]
      .sort((x, y) => y.to.length - x.to.length)
      .find((item) => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`))
    return match?.label ?? 'Ars Memoriae'
  }, [location.pathname])

  useEffect(() => {
    document.title = pageTitle === 'Ars Memoriae' ? pageTitle : `${pageTitle} · Ars Memoriae`
  }, [pageTitle])

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-2.5 py-1.5 text-xs font-medium whitespace-nowrap shrink-0 transition-colors ${
      isActive ? 'bg-sky-500/15 text-sky-200' : 'text-slate-400 hover:bg-ink-soft hover:text-slate-200'
    }`

  return (
    <div className={`min-h-screen ${isFullscreen ? 'bg-ink' : ''}`}>
      <a href="#main" className="skip-link">
        Skip to content
      </a>

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
        onFocus={() => setHeaderHovered(true)}
        onBlur={() => setHeaderHovered(false)}
        className={`sticky top-0 z-20 border-b border-ink-line bg-ink/90 backdrop-blur transition-all duration-200 ${
          hideHeader
            ? '-translate-y-full opacity-0 pointer-events-none'
            : 'translate-y-0 opacity-100 pointer-events-auto'
        }`}
      >
        <div
          className={
            isWide
              ? 'mx-auto flex w-full max-w-[2300px] items-center justify-between gap-4 px-4 py-2.5'
              : 'mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-2.5 sm:px-6 sm:py-3'
          }
        >
          {/* Zone 1: Brand wordmark */}
          <Link
            to="/"
            className="shrink-0 whitespace-nowrap text-sm font-semibold tracking-tight text-slate-100 hover:text-white transition rounded px-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            title="Ars Memoriae Dashboard"
            aria-label="Ars Memoriae, go to Review"
          >
            Ars Memoriae
          </Link>

          {/* Zone 2: Modular pinned navigation + More overflow */}
          <nav aria-label="Main" className="hidden lg:flex items-center gap-1 min-w-0">
            {pinnedNav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.to === '/code'} className={navLinkClass}>
                {item.label}
              </NavLink>
            ))}
            <MoreNavMenu
              unpinnedRoutes={unpinnedNav}
              onOpenCustomizer={() => setCustomizerOpen(true)}
              userEmail={user?.email}
              onSignOut={signOut}
            />
          </nav>

          {/* Zone 3: Workspace utility controls */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              aria-label="Open command search"
              title="Command palette (Ctrl/Cmd+K)"
              className="hidden sm:flex items-center gap-2 rounded-lg border border-ink-line bg-ink-soft px-2.5 py-1 text-xs text-slate-300 hover:border-slate-500 hover:text-slate-100 transition-colors cursor-pointer whitespace-nowrap shrink-0"
            >
              <svg
                className="h-3.5 w-3.5 text-slate-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
              <span>Search</span>
              <kbd className="font-mono text-[0.625rem] text-slate-500">⌘K</kbd>
            </button>

            <button
              type="button"
              onClick={() => setCustomizerOpen(true)}
              aria-label="Customize workspace layout"
              title={`Workspace layout (${config.preset})`}
              className="flex items-center gap-1.5 rounded-lg border border-ink-line bg-ink-soft px-2.5 py-1 text-xs font-medium text-slate-200 hover:border-sky-500/50 hover:text-white transition-colors cursor-pointer whitespace-nowrap shrink-0"
            >
              <svg
                className="h-3.5 w-3.5 text-sky-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
              </svg>
              <span>Layout</span>
            </button>

            <div className="hidden sm:flex items-center gap-1.5">
              <ThemeNavButton />
              <LexiconNavButton />
              <FullscreenButton className="hidden md:flex" />
            </div>

            <button
              type="button"
              className="lg:hidden flex items-center gap-1.5 rounded-lg border border-ink-line bg-ink-soft px-2.5 py-1 text-xs font-semibold text-slate-200 hover:border-slate-500 whitespace-nowrap shrink-0 cursor-pointer"
              aria-expanded={menuOpen}
              aria-controls="main-menu"
              onClick={() => setMenuOpen((open) => !open)}
            >
              <svg
                className="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden="true"
              >
                {menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
              </svg>
              <span>Menu</span>
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav
            id="main-menu"
            aria-label="Main"
            className="lg:hidden border-t border-ink-line bg-ink px-4 py-3"
          >
            <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
              {availableNav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/code'}
                  className={(state) => `${navLinkClass(state)} !px-3 !py-2.5 !text-sm`}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-ink-line pt-3 text-xs text-slate-400">
              <div className="flex sm:hidden items-center gap-2">
                <ThemeNavButton />
                <LexiconNavButton />
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false)
                    setCommandPaletteOpen(true)
                  }}
                  className="rounded-lg border border-ink-line bg-ink-soft px-2.5 py-1 text-xs text-slate-200 cursor-pointer"
                >
                  Search
                </button>
              </div>
              <div className="flex w-full sm:w-auto items-center justify-between gap-2">
                <span className="truncate">{user?.email}</span>
                <button type="button" className="btn btn-danger px-2.5 py-1 text-xs shrink-0" onClick={signOut}>
                  Sign out
                </button>
              </div>
            </div>
          </nav>
        )}
      </header>

      {/* Floating HUD pill when in Fullscreen or Zen mode */}
      <FullscreenHud />

      <main
        id="main"
        tabIndex={-1}
        className={`outline-none ${
          isWide
            ? `mx-auto w-full max-w-[2300px] px-3 sm:px-4 ${isZenMode ? 'py-2' : 'py-4'}`
            : `mx-auto max-w-6xl px-4 sm:px-6 ${isZenMode ? 'py-4' : 'py-6 sm:py-8'}`
        }`}
      >
        {/* Code Lab and Pre-LeetCode render their own visible <h1>. */}
        {!location.pathname.startsWith('/code') && <h1 className="sr-only">{pageTitle}</h1>}
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

      <WorkspaceCustomizerDrawer />
      <CommandPalette />
      <DialogHost />
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
      <main>
        <Suspense
          fallback={
            <div className="flex min-h-screen items-center justify-center">
              <Spinner />
            </div>
          }
        >
          <Login />
        </Suspense>
      </main>
    )
  }

  return (
    <ThemeProvider>
      <WorkspaceProvider>
        <FullscreenProvider>
          <LexiconProvider>
            <AppLayout />
          </LexiconProvider>
        </FullscreenProvider>
      </WorkspaceProvider>
    </ThemeProvider>
  )
}
