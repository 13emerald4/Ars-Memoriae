import React, { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react'
import { storage } from '../utils/storage'

export type ThemeMode = 'dynamic' | 'fixed'

export type FontSize = 10 | 12 | 14 | 16 | 18 | 20
export const FONT_SIZES: readonly FontSize[] = [10, 12, 14, 16, 18, 20] as const

export type CognitiveTheme =
  | 'dark'
  | 'classic'
  | 'acquisition'
  | 'recall'
  | 'diagnostic'
  | 'flow'
  | 'mastery'
  | 'circadian'

export type CognitiveContextState =
  | 'dark'
  | 'acquisition'
  | 'recall'
  | 'diagnostic'
  | 'flow'
  | 'mastery'
  | 'circadian'
  | null

export interface ThemeMeta {
  id: CognitiveTheme
  label: string
  subtitle: string
  icon: string
  primaryColor: string
  secondaryColor: string
  bgCanvas: string
  bgCard: string
  borderColor: string
  bestFor: string
  psychology: string
}

export const THEME_REGISTRY: Record<CognitiveTheme, ThemeMeta> = {
  dark: {
    id: 'dark',
    label: 'Dark Mode (OLED Black)',
    subtitle: 'True Pitch Black & Neutral Contrast',
    icon: '',
    primaryColor: '#38bdf8',
    secondaryColor: '#94a3b8',
    bgCanvas: '#000000',
    bgCard: '#090a0f',
    borderColor: '#1a1d27',
    bestFor: 'OLED displays, low-light study & high-contrast distraction-free focus',
    psychology:
      'True pitch-black eliminates all peripheral photon luminescence, relieving ocular strain during extended sessions while keeping focus sharp.',
  },
  acquisition: {
    id: 'acquisition',
    label: 'Acquisition & Learning',
    subtitle: 'Azure & Emerald (Blue & Green)',
    icon: '',
    primaryColor: '#0ea5e9',
    secondaryColor: '#10b981',
    bgCanvas: '#0b1320',
    bgCard: '#111d30',
    borderColor: '#1e3a5f',
    bestFor: 'New cards, reading extracts, conceptual learning & tutorials',
    psychology:
      'Blue calms working memory friction and heart rate; emerald stimulates parasympathetic visual relaxation and signals positive comprehension without anxiety.',
  },
  recall: {
    id: 'recall',
    label: 'Active Recall & Testing',
    subtitle: 'Deep Indigo & Golden Ochre',
    icon: '',
    primaryColor: '#6366f1',
    secondaryColor: '#f59e0b',
    bgCanvas: '#0e0d1a',
    bgCard: '#161429',
    borderColor: '#2c2752',
    bestFor: 'Flashcard retrieval, occlusion masking & testing speed drills',
    psychology:
      'Indigo drives inward introspective attention; amber provides high-contrast desirable difficulty cues that sharpen retrieval alertness.',
  },
  diagnostic: {
    id: 'diagnostic',
    label: 'Diagnostic Lab',
    subtitle: 'Analytical Cyan & Soft Coral',
    icon: '',
    primaryColor: '#06b6d4',
    secondaryColor: '#f43f5e',
    bgCanvas: '#0a151d',
    bgCard: '#112330',
    borderColor: '#193e50',
    bestFor: 'Failed unit tests, syntax errors, bug fixing & Socratic hints',
    psychology:
      'Soft coral re-frames errors constructively without triggering amygdala threat/panic; analytical cyan stabilizes objective problem-solving.',
  },
  flow: {
    id: 'flow',
    label: 'Deep Flow & Code Immersion',
    subtitle: 'Monochrome Obsidian & Electric Cyan',
    icon: '',
    primaryColor: '#38bdf8',
    secondaryColor: '#64748b',
    bgCanvas: '#08090d',
    bgCard: '#0f1118',
    borderColor: '#1c202d',
    bestFor: 'Tiled side-by-side IDE, algorithmic coding & Zen fullscreen',
    psychology:
      'Near-zero peripheral color saturation frees working memory slots; razor-sharp electric cyan guides line focus without sensory distraction.',
  },
  mastery: {
    id: 'mastery',
    label: 'Mastery & Peak Synthesis',
    subtitle: 'Royal Violet & Radiant Gold',
    icon: '',
    primaryColor: '#8b5cf6',
    secondaryColor: '#eab308',
    bgCanvas: '#100b1c',
    bgCard: '#19122b',
    borderColor: '#352354',
    bestFor: 'Deck completion summaries, 100% viewed cards & athlete milestones',
    psychology:
      'Violet and gold trigger neuroplastic reward reinforcement and dopaminergic pride of accomplishment at session wrap-up.',
  },
  circadian: {
    id: 'circadian',
    label: 'Circadian Nocturnal',
    subtitle: 'Warm Amber & Candlelight',
    icon: '',
    primaryColor: '#f59e0b',
    secondaryColor: '#fde68a',
    bgCanvas: '#130f0a',
    bgCard: '#1c160f',
    borderColor: '#332415',
    bestFor: 'Late night reviews, evening reading & zero digital eye strain',
    psychology:
      'Filters high-energy short-wavelength blue light (<480nm) to preserve melatonin synthesis and sleep architecture.',
  },
  classic: {
    id: 'classic',
    label: 'Classic Ars Memoriae',
    subtitle: 'Default Dark Slate & Sky',
    icon: '',
    primaryColor: '#0ea5e9',
    secondaryColor: '#94a3b8',
    bgCanvas: '#0f1117',
    bgCard: '#171a23',
    borderColor: '#252938',
    bestFor: 'Balanced neutral palette for everyday general usage',
    psychology: 'Minimalist industrial dark slate substrate with muted accents.',
  },
}

function isNightNow(): boolean {
  const hours = new Date().getHours()
  return hours >= 20 || hours < 6
}

/** "#0b1320" -> "11 19 32", the form `rgb(var(--x) / <alpha>)` expects. */
function hexToChannels(hex: string): string {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.replace(/./g, (c) => c + c) : h
  const n = Number.parseInt(full, 16)
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`
}

interface ThemeContextValue {
  themeMode: ThemeMode
  setThemeMode: (mode: ThemeMode) => void
  fixedTheme: CognitiveTheme
  setFixedTheme: (theme: CognitiveTheme) => void
  activeTheme: CognitiveTheme
  cognitiveContext: CognitiveContextState
  setCognitiveContext: (context: CognitiveContextState) => void
  enableNightAutoShift: boolean
  setEnableNightAutoShift: (enabled: boolean) => void
  enableOledBlack: boolean
  setEnableOledBlack: (enabled: boolean) => void
  enableGreyscaleFriendly: boolean
  setEnableGreyscaleFriendly: (enabled: boolean) => void
  simulateGreyscale: boolean
  setSimulateGreyscale: (enabled: boolean) => void
  activeThemeMeta: ThemeMeta
  fontSize: FontSize
  setFontSize: (size: FontSize) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Theme Mode: 'dynamic' (auto context-adaptive) vs 'fixed' (user lock)
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    const saved = storage.get('memorization.themeMode')
    return saved === 'fixed' ? 'fixed' : 'dynamic'
  })

  // Fixed palette selection
  const [fixedTheme, setFixedThemeState] = useState<CognitiveTheme>(() => {
    const saved = storage.get('memorization.fixedTheme') as CognitiveTheme
    return saved && THEME_REGISTRY[saved] ? saved : 'acquisition'
  })

  // Dynamic context state supplied by active views (e.g. Review, CodeLab, Read)
  const [cognitiveContext, setCognitiveContext] = useState<CognitiveContextState>(null)

  // Auto night shift toggle for dynamic mode
  const [enableNightAutoShift, setEnableNightAutoShiftState] = useState<boolean>(() => {
    return storage.get('memorization.nightAutoShift') !== '0'
  })

  // Pure Black / OLED Dark canvas toggle (applies #000000 background across all themes)
  const [enableOledBlack, setEnableOledBlackState] = useState<boolean>(() => {
    return storage.get('memorization.oledDark') === '1'
  })

  // Greyscale & High-Contrast Mode for monochrome displays, OS color filters, and e-ink
  const [enableGreyscaleFriendly, setEnableGreyscaleFriendlyState] = useState<boolean>(() => {
    return storage.get('memorization.greyscaleFriendly') === '1'
  })

  // In-browser greyscale simulation preview (filter: grayscale(100%))
  const [simulateGreyscale, setSimulateGreyscaleState] = useState<boolean>(() => {
    return storage.get('memorization.simulateGreyscale') === '1'
  })

  // Font Size scale: 10, 12, 14, 16, 18, 20
  const [fontSize, setFontSizeState] = useState<FontSize>(() => {
    const saved = Number(storage.get('memorization.fontSize'))
    return (FONT_SIZES.includes(saved as FontSize) ? saved : 16) as FontSize
  })

  const setThemeMode = useCallback((mode: ThemeMode) => {
    setThemeModeState(mode)
    storage.set('memorization.themeMode', mode)
  }, [])

  const setFixedTheme = useCallback((theme: CognitiveTheme) => {
    setFixedThemeState(theme)
    storage.set('memorization.fixedTheme', theme)
  }, [])

  const setEnableNightAutoShift = useCallback((enabled: boolean) => {
    setEnableNightAutoShiftState(enabled)
    storage.set('memorization.nightAutoShift', enabled ? '1' : '0')
  }, [])

  const setEnableOledBlack = useCallback((enabled: boolean) => {
    setEnableOledBlackState(enabled)
    storage.set('memorization.oledDark', enabled ? '1' : '0')
  }, [])

  const setEnableGreyscaleFriendly = useCallback((enabled: boolean) => {
    setEnableGreyscaleFriendlyState(enabled)
    storage.set('memorization.greyscaleFriendly', enabled ? '1' : '0')
  }, [])

  const setSimulateGreyscale = useCallback((enabled: boolean) => {
    setSimulateGreyscaleState(enabled)
    storage.set('memorization.simulateGreyscale', enabled ? '1' : '0')
  }, [])

  const setFontSize = useCallback((size: FontSize) => {
    setFontSizeState(size)
    storage.set('memorization.fontSize', String(size))
  }, [])

  // Night is after 20:00 or before 06:00. Checked every minute: computed once
  // at load, a session that started in the afternoon never shifted.
  const [isNightTime, setIsNightTime] = useState(isNightNow)
  useEffect(() => {
    const timer = window.setInterval(() => setIsNightTime(isNightNow()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  // Compute active effective theme
  const activeTheme = useMemo<CognitiveTheme>(() => {
    if (themeMode === 'fixed') {
      return fixedTheme
    }

    // Dynamic Context-Adaptive calculation
    if (enableNightAutoShift && isNightTime) {
      return 'circadian'
    }

    if (cognitiveContext && THEME_REGISTRY[cognitiveContext]) {
      return cognitiveContext
    }

    // Default dynamic state is acquisition (learning/blue-green)
    return 'acquisition'
  }, [themeMode, fixedTheme, cognitiveContext, enableNightAutoShift, isNightTime])

  // Sync active theme and font size to DOM root <html data-theme="..."> and CSS variables
  useEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.setAttribute('data-theme', activeTheme)
    root.setAttribute('data-oled', enableOledBlack ? 'true' : 'false')
    root.setAttribute('data-greyscale', enableGreyscaleFriendly ? 'true' : 'false')
    root.setAttribute('data-simulate-greyscale', simulateGreyscale ? 'true' : 'false')
    root.setAttribute('data-font-size', String(fontSize))

    // Set root rem base and font-size CSS variable
    root.style.fontSize = `${fontSize}px`
    root.style.setProperty('--app-font-size', `${fontSize}px`)

    const meta = THEME_REGISTRY[activeTheme] || THEME_REGISTRY.dark
    const isPureBlack = enableOledBlack || activeTheme === 'dark'
    const bgCanvas = isPureBlack ? '#000000' : meta.bgCanvas
    const bgCard = isPureBlack ? '#090a0f' : meta.bgCard
    const border = enableGreyscaleFriendly ? '#64748b' : isPureBlack ? '#1a1d27' : meta.borderColor

    root.style.setProperty('--theme-bg-canvas', bgCanvas)
    root.style.setProperty('--theme-bg-card', bgCard)
    root.style.setProperty('--theme-border', border)
    // Channel form of the same colours, for Tailwind's opacity modifiers.
    root.style.setProperty('--theme-bg-canvas-rgb', hexToChannels(bgCanvas))
    root.style.setProperty('--theme-bg-card-rgb', hexToChannels(bgCard))
    root.style.setProperty('--theme-border-rgb', hexToChannels(border))
    root.style.setProperty('--theme-accent', meta.primaryColor)
    root.style.setProperty('--theme-accent-secondary', meta.secondaryColor)
  }, [activeTheme, enableOledBlack, enableGreyscaleFriendly, simulateGreyscale, fontSize])

  const activeThemeMeta = THEME_REGISTRY[activeTheme] || THEME_REGISTRY.dark

  const value = useMemo(
    () => ({
      themeMode,
      setThemeMode,
      fixedTheme,
      setFixedTheme,
      activeTheme,
      cognitiveContext,
      setCognitiveContext,
      enableNightAutoShift,
      setEnableNightAutoShift,
      enableOledBlack,
      setEnableOledBlack,
      enableGreyscaleFriendly,
      setEnableGreyscaleFriendly,
      simulateGreyscale,
      setSimulateGreyscale,
      activeThemeMeta,
      fontSize,
      setFontSize,
    }),
    [
      themeMode,
      setThemeMode,
      fixedTheme,
      setFixedTheme,
      activeTheme,
      cognitiveContext,
      setCognitiveContext,
      enableNightAutoShift,
      setEnableNightAutoShift,
      enableOledBlack,
      setEnableOledBlack,
      enableGreyscaleFriendly,
      setEnableGreyscaleFriendly,
      simulateGreyscale,
      setSimulateGreyscale,
      activeThemeMeta,
      fontSize,
      setFontSize,
    ],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return ctx
}
