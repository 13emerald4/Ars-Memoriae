import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react'

interface FullscreenContextValue {
  /** True when HTML5 native document fullscreen is active */
  isFullscreen: boolean
  /** True when distraction-free zen mode (collapsed header) is active */
  isZenMode: boolean
  /** Toggles native browser fullscreen */
  toggleFullscreen: () => Promise<void>
  /** Toggles distraction-free Zen mode (header auto-hide) */
  toggleZenMode: () => void
  /** Exits both native fullscreen and Zen mode */
  exitFullscreen: () => Promise<void>
}

const FullscreenContext = createContext<FullscreenContextValue | null>(null)

export function useFullscreen(): FullscreenContextValue {
  const ctx = useContext(FullscreenContext)
  if (!ctx) {
    throw new Error('useFullscreen must be used within a FullscreenProvider')
  }
  return ctx
}

const ZEN_MODE_STORAGE_KEY = 'memorization.zenMode'

function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false
  const tag = target.tagName.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return true
  if (target.isContentEditable) return true
  if (target.closest('.monaco-editor') || target.closest('[contenteditable="true"]')) return true
  return false
}

export function FullscreenProvider({ children }: { children: ReactNode }) {
  const [isFullscreen, setIsFullscreen] = useState<boolean>(() => {
    if (typeof document === 'undefined') return false
    return Boolean(document.fullscreenElement)
  })

  const [isZenMode, setIsZenMode] = useState<boolean>(() => {
    if (typeof localStorage === 'undefined') return false
    return localStorage.getItem(ZEN_MODE_STORAGE_KEY) === '1'
  })

  // Synchronize state with browser fullscreenchange events
  useEffect(() => {
    function handleFullscreenChange() {
      const active = Boolean(document.fullscreenElement)
      setIsFullscreen(active)
      if (!active) {
        // If native fullscreen was exited via Esc, also deactivate Zen mode if desired
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
    }
  }, [])

  const toggleFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        if (document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen()
        } else if ((document.documentElement as any).webkitRequestFullscreen) {
          await (document.documentElement as any).webkitRequestFullscreen()
        }
        setIsFullscreen(true)
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen()
        } else if ((document as any).webkitExitFullscreen) {
          await (document as any).webkitExitFullscreen()
        }
        setIsFullscreen(false)
      }
    } catch (err) {
      console.warn('Native fullscreen request rejected or not supported, falling back to Zen Mode:', err)
      // Fallback: toggle Zen distraction-free mode
      setIsZenMode((prev) => {
        const next = !prev
        localStorage.setItem(ZEN_MODE_STORAGE_KEY, next ? '1' : '0')
        return next
      })
    }
  }, [])

  const toggleZenMode = useCallback(() => {
    setIsZenMode((prev) => {
      const next = !prev
      localStorage.setItem(ZEN_MODE_STORAGE_KEY, next ? '1' : '0')
      return next
    })
  }, [])

  const exitFullscreen = useCallback(async () => {
    try {
      if (document.fullscreenElement) {
        if (document.exitFullscreen) {
          await document.exitFullscreen()
        } else if ((document as any).webkitExitFullscreen) {
          await (document as any).webkitExitFullscreen()
        }
      }
    } catch {
      // ignore
    }
    setIsFullscreen(false)
    setIsZenMode(false)
    localStorage.setItem(ZEN_MODE_STORAGE_KEY, '0')
  }, [])

  // Global keyboard shortcuts:
  // - Ctrl+Shift+F or Cmd+Shift+F: Toggle fullscreen
  // - F (when not focused in input/textarea/monaco): Toggle fullscreen
  // - Escape: Exit Zen mode if active
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const isCmdOrCtrl = e.ctrlKey || e.metaKey

      // Ctrl+Shift+F or Cmd+Shift+F
      if (isCmdOrCtrl && e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault()
        void toggleFullscreen()
        return
      }

      // Standalone 'F' key outside of text inputs / editors
      if (!isCmdOrCtrl && !e.altKey && !e.shiftKey && e.key.toLowerCase() === 'f') {
        if (!isInteractiveTarget(e.target)) {
          e.preventDefault()
          void toggleFullscreen()
          return
        }
      }

      // Escape key exits Zen mode
      if (e.key === 'Escape' && isZenMode && !document.fullscreenElement) {
        setIsZenMode(false)
        localStorage.setItem(ZEN_MODE_STORAGE_KEY, '0')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleFullscreen, isZenMode])

  return (
    <FullscreenContext.Provider
      value={{
        isFullscreen,
        isZenMode,
        toggleFullscreen,
        toggleZenMode,
        exitFullscreen,
      }}
    >
      {children}
    </FullscreenContext.Provider>
  )
}

/** Header toggle button for navbar and toolbars */
export function FullscreenButton({
  className = '',
  showLabel = true,
  size = 'md',
}: {
  className?: string
  showLabel?: boolean
  size?: 'sm' | 'md'
}) {
  const { isFullscreen, isZenMode, toggleFullscreen } = useFullscreen()
  const active = isFullscreen || isZenMode

  const paddingClass = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'

  return (
    <button
      type="button"
      onClick={() => void toggleFullscreen()}
      title={
        active
          ? 'Exit Fullscreen Mode (Esc or F)'
          : 'Enter Fullscreen Mode (F or Ctrl+Shift+F)'
      }
      className={`flex items-center gap-1.5 rounded-lg border font-semibold transition-all ${
        active
          ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-200 hover:bg-emerald-500/25 ring-1 ring-emerald-500/30'
          : 'border-slate-700/80 bg-slate-800/50 text-slate-300 hover:border-slate-600 hover:bg-slate-700/60 hover:text-white'
      } ${paddingClass} ${className}`}
    >
      <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {active ? (
          <>
            <path d="M8 3v3a2 2 0 0 1-2 2H3" />
            <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
            <path d="M3 16h3a2 2 0 0 1 2 2v3" />
            <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
          </>
        ) : (
          <>
            <path d="M8 3H5a2 2 0 0 0-2 2v3" />
            <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
            <path d="M3 16v3a2 2 0 0 0 2 2h3" />
            <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
          </>
        )}
      </svg>
      {showLabel && (
        <span>{active ? 'Exit Fullscreen' : 'Fullscreen'}</span>
      )}
    </button>
  )
}

/** Floating distraction-free HUD pill shown when in Fullscreen / Zen mode */
export function FullscreenHud() {
  const { isFullscreen, isZenMode, toggleZenMode, exitFullscreen } = useFullscreen()
  const [hovered, setHovered] = useState(false)

  // Only display the floating pill when in Fullscreen or Zen mode
  if (!isFullscreen && !isZenMode) return null

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ zIndex: 9990 }}
      className={`fixed top-3 right-4 flex items-center gap-1.5 rounded-full border border-sky-500/40 bg-slate-950/90 px-3 py-1.5 shadow-2xl backdrop-blur transition-all duration-200 ${
        hovered ? 'opacity-100 scale-100' : 'opacity-40 hover:opacity-100 hover:scale-105'
      }`}
    >
      <span className="text-xs text-sky-300 font-semibold flex items-center gap-1">
        <span className="text-[11px] font-mono uppercase tracking-wider text-slate-300">
          {isFullscreen ? 'Fullscreen' : 'Zen Focus'}
        </span>
      </span>

      <button
        type="button"
        onClick={toggleZenMode}
        title={isZenMode ? 'Show Navigation Header' : 'Hide Navigation Header (Zen Mode)'}
        className="rounded px-1.5 py-0.5 text-[11px] font-medium text-slate-400 hover:text-sky-200 hover:bg-slate-800 transition"
      >
        {isZenMode ? 'Show Nav' : 'Hide Nav'}
      </button>

      <button
        type="button"
        onClick={() => void exitFullscreen()}
        title="Exit Fullscreen (Esc)"
        className="rounded px-2 py-0.5 text-[11px] font-bold text-rose-300 hover:bg-rose-950/60 transition flex items-center gap-1"
      >
        <span>Exit</span>
        <kbd className="text-[9px] text-slate-500 font-mono ml-0.5">Esc</kbd>
      </button>
    </div>
  )
}
