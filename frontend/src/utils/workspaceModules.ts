export type WorkspacePresetId = 'focus' | 'standard' | 'research' | 'custom'

export type ReviewModuleId =
  | 'sessionTimer'
  | 'queueSummary'
  | 'deckStatsBar'
  | 'neuroToolbar'
  | 'thematicDocs'
  | 'confidenceScale'
  | 'lexiconMargin'

export type ReviewTopBarId = 'sessionTimer' | 'queueSummary' | 'deckStatsBar'

export type CodeLabModuleId = 'studioTimer' | 'testConsole' | 'editorFooterHints'

export type LexiconDockSide = 'right' | 'left' | 'hidden'

export type CanvasWidth = 'compact' | 'balanced' | 'wide'

export interface WorkspaceConfig {
  version: 1
  preset: WorkspacePresetId
  reviewModules: Record<ReviewModuleId, boolean>
  reviewTopOrder: ReviewTopBarId[]
  lexiconDockSide: LexiconDockSide
  canvasWidth: CanvasWidth
  pinnedNavRoutes: string[]
  codeLabModules: Record<CodeLabModuleId, boolean>
}

export interface ModuleMetadata<T extends string> {
  id: T
  label: string
  description: string
  reorderable?: boolean
}

export const REVIEW_MODULE_META: ModuleMetadata<ReviewModuleId>[] = [
  {
    id: 'sessionTimer',
    label: 'Session Timer',
    description: 'Pomodoro study block countdown & Time Bank bar',
    reorderable: true,
  },
  {
    id: 'queueSummary',
    label: 'Queue & Study Modes',
    description: 'Collection filter, due counts, and study mode switcher',
    reorderable: true,
  },
  {
    id: 'deckStatsBar',
    label: 'Deck Progress Bar',
    description: 'Mastery progress, unseen count, Persist & All Cards Run',
    reorderable: true,
  },
  {
    id: 'neuroToolbar',
    label: 'Neuro & Memory Tools',
    description: 'Mnemonic, Mutate Prompt, Associative & Hypothesis controls',
  },
  {
    id: 'thematicDocs',
    label: 'Thematic Documentation',
    description: 'Inline context and reference documentation strip on cards',
  },
  {
    id: 'confidenceScale',
    label: 'Confidence Scale',
    description: '1–4 Judgment of Learning calibration buttons',
  },
  {
    id: 'lexiconMargin',
    label: 'Concordance & Lexicon',
    description: 'Docked glossary & card-memory margin panel',
  },
]

export const CODELAB_MODULE_META: ModuleMetadata<CodeLabModuleId>[] = [
  {
    id: 'studioTimer',
    label: 'Reflex Timer',
    description: 'Live stopwatch in the Code Lab studio bar',
  },
  {
    id: 'testConsole',
    label: 'Testcase Console',
    description: 'Interactive testcases and execution results pane',
  },
  {
    id: 'editorFooterHints',
    label: 'Editor Shortcut Bar',
    description: 'Cursor coordinates and keyboard shortcut hints below editor',
  },
]

export interface NavRouteItem {
  to: string
  label: string
  description: string
  core?: boolean
}

export const ALL_NAV_ROUTES: NavRouteItem[] = [
  { to: '/review', label: 'Review', description: 'Active-recall spaced repetition queue', core: true },
  { to: '/decks', label: 'Decks', description: 'Browse, organize, and create decks & cards' },
  { to: '/code', label: 'Code Lab', description: 'Algorithmic coding studio & test runner' },
  { to: '/code/fundamentals', label: 'Pre-LeetCode', description: 'MIT 6.0001 structured coding drills' },
  { to: '/tree', label: 'Tree', description: 'Knowledge hierarchy & mastery gating' },
  { to: '/read', label: 'Read', description: 'Incremental reading sources & extracts' },
  { to: '/stats', label: 'Stats', description: 'Retention, heatmap & learning analytics' },
  { to: '/tutorial', label: 'Start here', description: 'Interactive guide & workflow overview' },
  { to: '/settings', label: 'Settings', description: 'FSRS tuning, models & account preferences' },
]

export const DEFAULT_PINNED_NAV: string[] = ['/review', '/decks', '/code', '/read', '/stats']

export const DEFAULT_TOP_ORDER: ReviewTopBarId[] = ['queueSummary', 'deckStatsBar', 'sessionTimer']

export interface PresetDefinition {
  id: Exclude<WorkspacePresetId, 'custom'>
  label: string
  tagline: string
  reviewModules: Record<ReviewModuleId, boolean>
  lexiconDockSide: LexiconDockSide
  canvasWidth: CanvasWidth
  codeLabModules: Record<CodeLabModuleId, boolean>
}

export const WORKSPACE_PRESETS: Record<Exclude<WorkspacePresetId, 'custom'>, PresetDefinition> = {
  focus: {
    id: 'focus',
    label: 'Focus',
    tagline: 'Card-first active recall with zero chrome distraction',
    reviewModules: {
      sessionTimer: false,
      queueSummary: false,
      deckStatsBar: false,
      neuroToolbar: false,
      thematicDocs: false,
      confidenceScale: false,
      lexiconMargin: false,
    },
    lexiconDockSide: 'hidden',
    canvasWidth: 'compact',
    codeLabModules: {
      studioTimer: false,
      testConsole: true,
      editorFooterHints: false,
    },
  },
  standard: {
    id: 'standard',
    label: 'Standard',
    tagline: 'Clean balanced workbench with quick tools on demand',
    reviewModules: {
      sessionTimer: false,
      queueSummary: true,
      deckStatsBar: false,
      neuroToolbar: false,
      thematicDocs: true,
      confidenceScale: true,
      lexiconMargin: false,
    },
    lexiconDockSide: 'hidden',
    canvasWidth: 'balanced',
    codeLabModules: {
      studioTimer: true,
      testConsole: true,
      editorFooterHints: true,
    },
  },
  research: {
    id: 'research',
    label: 'Research',
    tagline: 'Full scholar cockpit with timer, neuro tools & lexicon margin',
    reviewModules: {
      sessionTimer: true,
      queueSummary: true,
      deckStatsBar: true,
      neuroToolbar: true,
      thematicDocs: true,
      confidenceScale: true,
      lexiconMargin: true,
    },
    lexiconDockSide: 'right',
    canvasWidth: 'wide',
    codeLabModules: {
      studioTimer: true,
      testConsole: true,
      editorFooterHints: true,
    },
  },
}

export function createDefaultWorkspaceConfig(): WorkspaceConfig {
  const std = WORKSPACE_PRESETS.standard
  return {
    version: 1,
    preset: 'standard',
    reviewModules: { ...std.reviewModules },
    reviewTopOrder: [...DEFAULT_TOP_ORDER],
    lexiconDockSide: std.lexiconDockSide,
    canvasWidth: std.canvasWidth,
    pinnedNavRoutes: [...DEFAULT_PINNED_NAV],
    codeLabModules: { ...std.codeLabModules },
  }
}

export function applyWorkspacePreset(
  current: WorkspaceConfig,
  presetId: Exclude<WorkspacePresetId, 'custom'>,
): WorkspaceConfig {
  const preset = WORKSPACE_PRESETS[presetId]
  return {
    ...current,
    preset: presetId,
    reviewModules: { ...preset.reviewModules },
    lexiconDockSide: preset.lexiconDockSide,
    canvasWidth: preset.canvasWidth,
    codeLabModules: { ...preset.codeLabModules },
  }
}

export function toggleReviewModule(
  current: WorkspaceConfig,
  moduleId: ReviewModuleId,
): WorkspaceConfig {
  const nextVal = !current.reviewModules[moduleId]
  const nextModules = { ...current.reviewModules, [moduleId]: nextVal }
  let nextDock = current.lexiconDockSide
  if (moduleId === 'lexiconMargin') {
    nextDock = nextVal ? (current.lexiconDockSide === 'hidden' ? 'right' : current.lexiconDockSide) : 'hidden'
  }
  return {
    ...current,
    preset: 'custom',
    reviewModules: nextModules,
    lexiconDockSide: nextDock,
  }
}

export function toggleCodeLabModule(
  current: WorkspaceConfig,
  moduleId: CodeLabModuleId,
): WorkspaceConfig {
  return {
    ...current,
    preset: 'custom',
    codeLabModules: {
      ...current.codeLabModules,
      [moduleId]: !current.codeLabModules[moduleId],
    },
  }
}

export function setLexiconDockSide(
  current: WorkspaceConfig,
  side: LexiconDockSide,
): WorkspaceConfig {
  return {
    ...current,
    preset: 'custom',
    lexiconDockSide: side,
    reviewModules: {
      ...current.reviewModules,
      lexiconMargin: side !== 'hidden',
    },
  }
}

export function setCanvasWidth(current: WorkspaceConfig, width: CanvasWidth): WorkspaceConfig {
  return {
    ...current,
    preset: 'custom',
    canvasWidth: width,
  }
}

export function moveReviewTopBar(
  current: WorkspaceConfig,
  barId: ReviewTopBarId,
  direction: 'up' | 'down',
): WorkspaceConfig {
  const order = [...current.reviewTopOrder]
  const idx = order.indexOf(barId)
  if (idx === -1) return current
  const target = direction === 'up' ? idx - 1 : idx + 1
  if (target < 0 || target >= order.length) return current
  const tmp = order[target]
  order[target] = order[idx]
  order[idx] = tmp
  return {
    ...current,
    preset: 'custom',
    reviewTopOrder: order,
  }
}

export function togglePinnedNavRoute(current: WorkspaceConfig, route: string): WorkspaceConfig {
  // Always keep /review pinned as the primary home anchor
  if (route === '/review') return current
  const exists = current.pinnedNavRoutes.includes(route)
  const validRoutes = new Set(ALL_NAV_ROUTES.map((r) => r.to))
  if (!validRoutes.has(route)) return current

  const next = exists
    ? current.pinnedNavRoutes.filter((r) => r !== route)
    : [...current.pinnedNavRoutes, route]

  // Preserve canonical nav order so pinned links stay predictable
  const canonical = ALL_NAV_ROUTES.map((r) => r.to)
  const sorted = canonical.filter((r) => next.includes(r))
  return {
    ...current,
    pinnedNavRoutes: sorted,
  }
}

export function sanitizeWorkspaceConfig(raw: unknown): WorkspaceConfig {
  const defaults = createDefaultWorkspaceConfig()
  if (!raw || typeof raw !== 'object') return defaults
  const obj = raw as Record<string, unknown>

  const presetVal = obj.preset
  const preset: WorkspacePresetId =
    presetVal === 'focus' || presetVal === 'standard' || presetVal === 'research' || presetVal === 'custom'
      ? presetVal
      : defaults.preset

  const rawReview = (obj.reviewModules && typeof obj.reviewModules === 'object'
    ? obj.reviewModules
    : {}) as Record<string, unknown>
  const reviewModules: Record<ReviewModuleId, boolean> = {
    sessionTimer:
      typeof rawReview.sessionTimer === 'boolean' ? rawReview.sessionTimer : defaults.reviewModules.sessionTimer,
    queueSummary:
      typeof rawReview.queueSummary === 'boolean' ? rawReview.queueSummary : defaults.reviewModules.queueSummary,
    deckStatsBar:
      typeof rawReview.deckStatsBar === 'boolean' ? rawReview.deckStatsBar : defaults.reviewModules.deckStatsBar,
    neuroToolbar:
      typeof rawReview.neuroToolbar === 'boolean' ? rawReview.neuroToolbar : defaults.reviewModules.neuroToolbar,
    thematicDocs:
      typeof rawReview.thematicDocs === 'boolean' ? rawReview.thematicDocs : defaults.reviewModules.thematicDocs,
    confidenceScale:
      typeof rawReview.confidenceScale === 'boolean'
        ? rawReview.confidenceScale
        : defaults.reviewModules.confidenceScale,
    lexiconMargin:
      typeof rawReview.lexiconMargin === 'boolean' ? rawReview.lexiconMargin : defaults.reviewModules.lexiconMargin,
  }

  const validTopBars: ReviewTopBarId[] = ['sessionTimer', 'queueSummary', 'deckStatsBar']
  let reviewTopOrder = [...DEFAULT_TOP_ORDER]
  if (Array.isArray(obj.reviewTopOrder)) {
    const filtered = obj.reviewTopOrder.filter((x): x is ReviewTopBarId =>
      validTopBars.includes(x as ReviewTopBarId),
    )
    const unique = Array.from(new Set(filtered))
    for (const bar of validTopBars) {
      if (!unique.includes(bar)) unique.push(bar)
    }
    reviewTopOrder = unique
  }

  const rawDock = obj.lexiconDockSide
  const lexiconDockSide: LexiconDockSide =
    rawDock === 'left' || rawDock === 'right' || rawDock === 'hidden'
      ? rawDock
      : reviewModules.lexiconMargin
        ? 'right'
        : 'hidden'

  // Keep lexiconMargin boolean and dock side strictly consistent
  reviewModules.lexiconMargin = lexiconDockSide !== 'hidden'

  const rawWidth = obj.canvasWidth
  const canvasWidth: CanvasWidth =
    rawWidth === 'compact' || rawWidth === 'balanced' || rawWidth === 'wide' ? rawWidth : defaults.canvasWidth

  const validNavSet = new Set(ALL_NAV_ROUTES.map((r) => r.to))
  let pinnedNavRoutes = [...DEFAULT_PINNED_NAV]
  if (Array.isArray(obj.pinnedNavRoutes)) {
    const filtered = obj.pinnedNavRoutes.filter(
      (r): r is string => typeof r === 'string' && validNavSet.has(r),
    )
    if (!filtered.includes('/review')) filtered.unshift('/review')
    pinnedNavRoutes = ALL_NAV_ROUTES.map((r) => r.to).filter((r) => filtered.includes(r))
  }

  const rawCode = (obj.codeLabModules && typeof obj.codeLabModules === 'object'
    ? obj.codeLabModules
    : {}) as Record<string, unknown>
  const codeLabModules: Record<CodeLabModuleId, boolean> = {
    studioTimer:
      typeof rawCode.studioTimer === 'boolean' ? rawCode.studioTimer : defaults.codeLabModules.studioTimer,
    testConsole:
      typeof rawCode.testConsole === 'boolean' ? rawCode.testConsole : defaults.codeLabModules.testConsole,
    editorFooterHints:
      typeof rawCode.editorFooterHints === 'boolean'
        ? rawCode.editorFooterHints
        : defaults.codeLabModules.editorFooterHints,
  }

  return {
    version: 1,
    preset,
    reviewModules,
    reviewTopOrder,
    lexiconDockSide,
    canvasWidth,
    pinnedNavRoutes,
    codeLabModules,
  }
}

export interface CommandItem {
  id: string
  group: 'Navigate' | 'Workspace Preset' | 'Toggle Module' | 'Action'
  label: string
  hint?: string
  keywords?: string[]
  active?: boolean
}

export function filterCommandItems<T extends CommandItem>(items: T[], query: string): T[] {
  const q = query.trim().toLowerCase()
  if (!q) return items
  const tokens = q.split(/\s+/).filter(Boolean)
  return items.filter((item) => {
    const haystack = [item.label, item.group, item.hint || '', ...(item.keywords || [])]
      .join(' ')
      .toLowerCase()
    return tokens.every((t) => haystack.includes(t))
  })
}

export function getCanvasMaxWidthClass(width: CanvasWidth, hasSidePanel: boolean): string {
  if (hasSidePanel) {
    if (width === 'compact') return 'max-w-3xl'
    if (width === 'wide') return 'max-w-5xl'
    return 'max-w-4xl'
  }
  if (width === 'compact') return 'max-w-2xl'
  if (width === 'wide') return 'max-w-5xl'
  return 'max-w-3xl'
}
