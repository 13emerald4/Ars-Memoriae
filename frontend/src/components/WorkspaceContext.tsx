import { createContext, startTransition, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { storage } from '../utils/storage'
import { runViewTransition } from '../utils/viewTransition'
import {
  applyWorkspacePreset,
  createDefaultWorkspaceConfig,
  moveReviewTopBar,
  sanitizeWorkspaceConfig,
  setCanvasWidth as setCanvasWidthPure,
  setLexiconDockSide as setLexiconDockSidePure,
  toggleCodeLabModule as toggleCodeLabModulePure,
  togglePinnedNavRoute as togglePinnedNavRoutePure,
  toggleReviewModule as toggleReviewModulePure,
  type CanvasWidth,
  type CodeLabModuleId,
  type LexiconDockSide,
  type ReviewModuleId,
  type ReviewTopBarId,
  type WorkspaceConfig,
  type WorkspacePresetId,
} from '../utils/workspaceModules'

const STORAGE_KEY = 'ars.workspace.v1'

function loadInitialConfig(): WorkspaceConfig {
  try {
    const raw = storage.get(STORAGE_KEY)
    if (!raw) return createDefaultWorkspaceConfig()
    return sanitizeWorkspaceConfig(JSON.parse(raw))
  } catch {
    return createDefaultWorkspaceConfig()
  }
}

interface WorkspaceContextValue {
  config: WorkspaceConfig
  applyPreset: (preset: Exclude<WorkspacePresetId, 'custom'>) => void
  toggleReviewModule: (id: ReviewModuleId) => void
  toggleCodeLabModule: (id: CodeLabModuleId) => void
  moveTopBar: (id: ReviewTopBarId, dir: 'up' | 'down') => void
  setLexiconSide: (side: LexiconDockSide) => void
  setCanvasWidth: (width: CanvasWidth) => void
  togglePinnedNav: (route: string) => void
  resetWorkspace: () => void
  customizerOpen: boolean
  setCustomizerOpen: (open: boolean) => void
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<WorkspaceConfig>(loadInitialConfig)
  const [customizerOpen, setCustomizerOpen] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  useEffect(() => {
    try {
      storage.set(STORAGE_KEY, JSON.stringify(config))
    } catch {
      /* ignore private-mode storage failures */
    }
  }, [config])

  // Global Cmd/Ctrl+K shortcut for Command Palette
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandPaletteOpen((open) => !open)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const applyPreset = useCallback((preset: Exclude<WorkspacePresetId, 'custom'>) => {
    runViewTransition(() => {
      startTransition(() => {
        setConfig((prev) => applyWorkspacePreset(prev, preset))
      })
    })
  }, [])

  const toggleReviewModule = useCallback((id: ReviewModuleId) => {
    startTransition(() => {
      setConfig((prev) => toggleReviewModulePure(prev, id))
    })
  }, [])

  const toggleCodeLabModule = useCallback((id: CodeLabModuleId) => {
    startTransition(() => {
      setConfig((prev) => toggleCodeLabModulePure(prev, id))
    })
  }, [])

  const moveTopBar = useCallback((id: ReviewTopBarId, dir: 'up' | 'down') => {
    setConfig((prev) => moveReviewTopBar(prev, id, dir))
  }, [])

  const setLexiconSide = useCallback((side: LexiconDockSide) => {
    runViewTransition(() => {
      startTransition(() => {
        setConfig((prev) => setLexiconDockSidePure(prev, side))
      })
    })
  }, [])

  const setCanvasWidth = useCallback((width: CanvasWidth) => {
    runViewTransition(() => {
      startTransition(() => {
        setConfig((prev) => setCanvasWidthPure(prev, width))
      })
    })
  }, [])

  const togglePinnedNav = useCallback((route: string) => {
    setConfig((prev) => togglePinnedNavRoutePure(prev, route))
  }, [])

  const resetWorkspace = useCallback(() => {
    runViewTransition(() => {
      startTransition(() => {
        setConfig(createDefaultWorkspaceConfig())
      })
    })
  }, [])

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      config,
      applyPreset,
      toggleReviewModule,
      toggleCodeLabModule,
      moveTopBar,
      setLexiconSide,
      setCanvasWidth,
      togglePinnedNav,
      resetWorkspace,
      customizerOpen,
      setCustomizerOpen,
      commandPaletteOpen,
      setCommandPaletteOpen,
    }),
    [
      config,
      applyPreset,
      toggleReviewModule,
      toggleCodeLabModule,
      moveTopBar,
      setLexiconSide,
      setCanvasWidth,
      togglePinnedNav,
      resetWorkspace,
      customizerOpen,
      commandPaletteOpen,
    ],
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider')
  }
  return ctx
}
