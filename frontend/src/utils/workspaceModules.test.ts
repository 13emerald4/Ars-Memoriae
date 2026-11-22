import test from 'node:test'
import assert from 'node:assert/strict'
import {
  applyWorkspacePreset,
  createDefaultWorkspaceConfig,
  filterCommandItems,
  getCanvasMaxWidthClass,
  moveReviewTopBar,
  sanitizeWorkspaceConfig,
  setCanvasWidth,
  setLexiconDockSide,
  toggleCodeLabModule,
  togglePinnedNavRoute,
  toggleReviewModule,
  type CommandItem,
} from './workspaceModules'

test('default workspace uses standard preset with clean defaults', () => {
  const cfg = createDefaultWorkspaceConfig()
  assert.equal(cfg.preset, 'standard')
  assert.equal(cfg.reviewModules.sessionTimer, false)
  assert.equal(cfg.reviewModules.queueSummary, true)
  assert.equal(cfg.reviewModules.deckStatsBar, false)
  assert.equal(cfg.reviewModules.lexiconMargin, false)
  assert.equal(cfg.lexiconDockSide, 'hidden')
  assert.ok(cfg.pinnedNavRoutes.includes('/review'))
})

test('applyWorkspacePreset switches between focus, standard, and research cleanly', () => {
  const base = createDefaultWorkspaceConfig()
  const focus = applyWorkspacePreset(base, 'focus')
  assert.equal(focus.preset, 'focus')
  assert.equal(focus.reviewModules.queueSummary, false)
  assert.equal(focus.reviewModules.deckStatsBar, false)
  assert.equal(focus.reviewModules.confidenceScale, false)
  assert.equal(focus.lexiconDockSide, 'hidden')
  assert.equal(focus.canvasWidth, 'compact')

  const research = applyWorkspacePreset(focus, 'research')
  assert.equal(research.preset, 'research')
  assert.equal(research.reviewModules.sessionTimer, true)
  assert.equal(research.reviewModules.neuroToolbar, true)
  assert.equal(research.reviewModules.lexiconMargin, true)
  assert.equal(research.lexiconDockSide, 'right')
  assert.equal(research.canvasWidth, 'wide')
})

test('toggling modules switches preset to custom and keeps lexicon dock synced', () => {
  const base = createDefaultWorkspaceConfig()
  const withLex = toggleReviewModule(base, 'lexiconMargin')
  assert.equal(withLex.preset, 'custom')
  assert.equal(withLex.reviewModules.lexiconMargin, true)
  assert.equal(withLex.lexiconDockSide, 'right')

  const dockedLeft = setLexiconDockSide(withLex, 'left')
  assert.equal(dockedLeft.lexiconDockSide, 'left')
  assert.equal(dockedLeft.reviewModules.lexiconMargin, true)

  const hiddenAgain = setLexiconDockSide(dockedLeft, 'hidden')
  assert.equal(hiddenAgain.reviewModules.lexiconMargin, false)
  assert.equal(hiddenAgain.lexiconDockSide, 'hidden')
})

test('moveReviewTopBar reorders modules and ignores out-of-bounds moves', () => {
  const base = createDefaultWorkspaceConfig()
  assert.deepEqual(base.reviewTopOrder, ['queueSummary', 'deckStatsBar', 'sessionTimer'])

  const movedUp = moveReviewTopBar(base, 'sessionTimer', 'up')
  assert.deepEqual(movedUp.reviewTopOrder, ['queueSummary', 'sessionTimer', 'deckStatsBar'])

  const noOp = moveReviewTopBar(movedUp, 'queueSummary', 'up')
  assert.deepEqual(noOp.reviewTopOrder, ['queueSummary', 'sessionTimer', 'deckStatsBar'])
})

test('togglePinnedNavRoute keeps /review locked and maintains canonical order', () => {
  const base = createDefaultWorkspaceConfig()
  const unchanged = togglePinnedNavRoute(base, '/review')
  assert.deepEqual(unchanged.pinnedNavRoutes, base.pinnedNavRoutes)

  const addedTree = togglePinnedNavRoute(base, '/tree')
  assert.ok(addedTree.pinnedNavRoutes.includes('/tree'))
  assert.ok(addedTree.pinnedNavRoutes.indexOf('/tree') < addedTree.pinnedNavRoutes.indexOf('/read'))

  const removedStats = togglePinnedNavRoute(addedTree, '/stats')
  assert.equal(removedStats.pinnedNavRoutes.includes('/stats'), false)
})

test('toggleCodeLabModule and setCanvasWidth update cleanly', () => {
  const base = createDefaultWorkspaceConfig()
  const toggled = toggleCodeLabModule(base, 'testConsole')
  assert.equal(toggled.codeLabModules.testConsole, false)
  assert.equal(toggled.preset, 'custom')

  const wide = setCanvasWidth(toggled, 'wide')
  assert.equal(wide.canvasWidth, 'wide')
  assert.equal(getCanvasMaxWidthClass('compact', false), 'max-w-2xl')
  assert.equal(getCanvasMaxWidthClass('wide', true), 'max-w-5xl')
})

test('sanitizeWorkspaceConfig recovers cleanly from corrupt or partial JSON', () => {
  const fallback = sanitizeWorkspaceConfig(null)
  assert.equal(fallback.preset, 'standard')

  const partial = sanitizeWorkspaceConfig({
    preset: 'bogus',
    reviewModules: { sessionTimer: true, lexiconMargin: true },
    reviewTopOrder: ['sessionTimer', 'invalid_bar'],
    lexiconDockSide: 'left',
    pinnedNavRoutes: ['/decks', '/nonexistent'],
  })
  assert.equal(partial.preset, 'standard')
  assert.equal(partial.reviewModules.sessionTimer, true)
  assert.equal(partial.reviewModules.lexiconMargin, true)
  assert.equal(partial.lexiconDockSide, 'left')
  assert.deepEqual(partial.reviewTopOrder, ['sessionTimer', 'queueSummary', 'deckStatsBar'])
  assert.deepEqual(partial.pinnedNavRoutes, ['/review', '/decks'])
})

test('filterCommandItems supports multi-word fuzzy matching', () => {
  const items: CommandItem[] = [
    { id: '1', group: 'Navigate', label: 'Code Lab', keywords: ['algorithms', 'leetcode'] },
    { id: '2', group: 'Toggle Module', label: 'Session Timer', hint: 'Review workspace' },
    { id: '3', group: 'Workspace Preset', label: 'Focus Mode', hint: 'Minimal distraction' },
  ]
  assert.equal(filterCommandItems(items, '').length, 3)
  assert.deepEqual(
    filterCommandItems(items, 'code algo').map((i) => i.id),
    ['1'],
  )
  assert.deepEqual(
    filterCommandItems(items, 'toggle timer').map((i) => i.id),
    ['2'],
  )
  assert.equal(filterCommandItems(items, 'nonexistent').length, 0)
})
