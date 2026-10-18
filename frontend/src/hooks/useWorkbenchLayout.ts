import { useCallback, useEffect, useState } from 'react'

export interface WorkbenchLayoutState {
  leftWidthPercent: number
  tiledLeftWidthPercent: number
  editorHeight: number
  columnsSwapped: boolean
  isStacked: boolean
  leftCollapsed: boolean
  consoleCollapsed: boolean
  consoleDockPosition: 'bottom' | 'right'
  consoleWidthPercent: number
}

const STORAGE_KEY = 'memorization.reviewWorkbenchLayout'

export const DEFAULT_WORKBENCH_LAYOUT: WorkbenchLayoutState = {
  leftWidthPercent: 38,
  tiledLeftWidthPercent: 50,
  editorHeight: 460,
  columnsSwapped: false,
  isStacked: false,
  leftCollapsed: false,
  consoleCollapsed: false,
  consoleDockPosition: 'bottom',
  consoleWidthPercent: 38,
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function loadLayoutState(): WorkbenchLayoutState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_WORKBENCH_LAYOUT
    const parsed = JSON.parse(raw)
    return {
      leftWidthPercent: clamp(
        typeof parsed.leftWidthPercent === 'number' ? parsed.leftWidthPercent : DEFAULT_WORKBENCH_LAYOUT.leftWidthPercent,
        18,
        80,
      ),
      tiledLeftWidthPercent: clamp(
        typeof parsed.tiledLeftWidthPercent === 'number' ? parsed.tiledLeftWidthPercent : DEFAULT_WORKBENCH_LAYOUT.tiledLeftWidthPercent,
        20,
        80,
      ),
      editorHeight: clamp(
        typeof parsed.editorHeight === 'number' ? parsed.editorHeight : DEFAULT_WORKBENCH_LAYOUT.editorHeight,
        240,
        950,
      ),
      columnsSwapped: Boolean(parsed.columnsSwapped),
      isStacked: Boolean(parsed.isStacked),
      leftCollapsed: Boolean(parsed.leftCollapsed),
      consoleCollapsed: Boolean(parsed.consoleCollapsed),
      consoleDockPosition: parsed.consoleDockPosition === 'right' ? 'right' : 'bottom',
      consoleWidthPercent: clamp(
        typeof parsed.consoleWidthPercent === 'number' ? parsed.consoleWidthPercent : DEFAULT_WORKBENCH_LAYOUT.consoleWidthPercent,
        20,
        70,
      ),
    }
  } catch {
    return DEFAULT_WORKBENCH_LAYOUT
  }
}

export function useWorkbenchLayout() {
  const [layout, setLayout] = useState<WorkbenchLayoutState>(loadLayoutState)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout))
    } catch {
      // Ignore quota errors
    }
  }, [layout])

  const handleMainResize = useCallback((deltaPx: number, containerWidthPx: number) => {
    if (!containerWidthPx || containerWidthPx <= 0) return
    const deltaPercent = (deltaPx / containerWidthPx) * 100

    setLayout((prev) => {
      // If columns are swapped: left is workbench, right is problem
      const change = prev.columnsSwapped ? -deltaPercent : deltaPercent
      const nextPercent = clamp(prev.leftWidthPercent + change, 18, 80)
      return { ...prev, leftWidthPercent: Math.round(nextPercent * 10) / 10, leftCollapsed: false }
    })
  }, [])

  const handleTiledResize = useCallback((deltaPx: number, containerWidthPx: number) => {
    if (!containerWidthPx || containerWidthPx <= 0) return
    const deltaPercent = (deltaPx / containerWidthPx) * 100

    setLayout((prev) => {
      const nextPercent = clamp(prev.tiledLeftWidthPercent + deltaPercent, 20, 80)
      return { ...prev, tiledLeftWidthPercent: Math.round(nextPercent * 10) / 10 }
    })
  }, [])

  const handleEditorHeightResize = useCallback((deltaPx: number) => {
    setLayout((prev) => {
      const nextHeight = clamp(prev.editorHeight + deltaPx, 240, 950)
      return { ...prev, editorHeight: Math.round(nextHeight), consoleCollapsed: false }
    })
  }, [])

  const handleConsoleWidthResize = useCallback((deltaPx: number, containerWidthPx: number) => {
    if (!containerWidthPx || containerWidthPx <= 0) return
    const deltaPercent = (deltaPx / containerWidthPx) * 100

    setLayout((prev) => {
      const nextPercent = clamp(prev.consoleWidthPercent - deltaPercent, 20, 70)
      return { ...prev, consoleWidthPercent: Math.round(nextPercent * 10) / 10, consoleCollapsed: false }
    })
  }, [])

  const toggleColumnsSwapped = useCallback(() => {
    setLayout((prev) => ({ ...prev, columnsSwapped: !prev.columnsSwapped }))
  }, [])

  const toggleStacked = useCallback(() => {
    setLayout((prev) => ({ ...prev, isStacked: !prev.isStacked }))
  }, [])

  const toggleLeftCollapsed = useCallback(() => {
    setLayout((prev) => ({ ...prev, leftCollapsed: !prev.leftCollapsed }))
  }, [])

  const toggleConsoleCollapsed = useCallback(() => {
    setLayout((prev) => ({ ...prev, consoleCollapsed: !prev.consoleCollapsed }))
  }, [])

  const setConsoleDockPosition = useCallback((pos: 'bottom' | 'right') => {
    setLayout((prev) => ({ ...prev, consoleDockPosition: pos, consoleCollapsed: false }))
  }, [])

  const resetLayout = useCallback(() => {
    setLayout(DEFAULT_WORKBENCH_LAYOUT)
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // Ignore
    }
  }, [])

  const resetMainSplit = useCallback(() => {
    setLayout((prev) => ({ ...prev, leftWidthPercent: DEFAULT_WORKBENCH_LAYOUT.leftWidthPercent, leftCollapsed: false }))
  }, [])

  const resetTiledSplit = useCallback(() => {
    setLayout((prev) => ({ ...prev, tiledLeftWidthPercent: DEFAULT_WORKBENCH_LAYOUT.tiledLeftWidthPercent }))
  }, [])

  const resetEditorHeight = useCallback(() => {
    setLayout((prev) => ({ ...prev, editorHeight: DEFAULT_WORKBENCH_LAYOUT.editorHeight, consoleCollapsed: false }))
  }, [])

  const resetConsoleWidth = useCallback(() => {
    setLayout((prev) => ({ ...prev, consoleWidthPercent: DEFAULT_WORKBENCH_LAYOUT.consoleWidthPercent, consoleCollapsed: false }))
  }, [])

  return {
    ...layout,
    handleMainResize,
    handleTiledResize,
    handleEditorHeightResize,
    handleConsoleWidthResize,
    toggleColumnsSwapped,
    toggleStacked,
    toggleLeftCollapsed,
    toggleConsoleCollapsed,
    setConsoleDockPosition,
    resetLayout,
    resetMainSplit,
    resetTiledSplit,
    resetEditorHeight,
    resetConsoleWidth,
  }
}

export default useWorkbenchLayout
