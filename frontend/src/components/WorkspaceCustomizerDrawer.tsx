import { useAuth } from '../hooks/useAuth'
import { NativeDialog } from './NativeDialog'
import {
  ALL_NAV_ROUTES,
  CODELAB_MODULE_META,
  REVIEW_MODULE_META,
  WORKSPACE_PRESETS,
  type CanvasWidth,
  type LexiconDockSide,
  type ReviewTopBarId,
} from '../utils/workspaceModules'
import { useWorkspace } from './WorkspaceContext'

const TOP_BAR_LABELS: Record<ReviewTopBarId, string> = {
  queueSummary: 'Queue & Study Modes',
  deckStatsBar: 'Deck Progress Bar',
  sessionTimer: 'Session Timer',
}

export function WorkspaceCustomizerDrawer() {
  const { user } = useAuth()
  const {
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
  } = useWorkspace()

  if (!customizerOpen) return null

  const availableNav = ALL_NAV_ROUTES.filter((item) => {
    if (item.to === '/code/fundamentals' && user?.show_pre_leetcode === false) return false
    if (item.to === '/code' && user?.show_code_lab === false) return false
    return true
  })

  return (
    <NativeDialog
      open={customizerOpen}
      onClose={() => setCustomizerOpen(false)}
      ariaLabel="Workspace Layout"
      variant="drawer"
      className="w-full max-w-md"
    >
      <aside className="flex h-full w-full flex-col border-l border-ink-line bg-ink text-slate-200 shadow-2xl outline-none">
        <div className="flex items-center justify-between border-b border-ink-line px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Workspace Layout</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              Show, hide, dock, or reorder modules to match how you study.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setCustomizerOpen(false)}
            aria-label="Close workspace layout"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-ink-line bg-ink-soft text-slate-300 hover:border-slate-500 hover:text-white transition-colors cursor-pointer"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6 scroll-stable">
          {/* 1. Workspace Presets */}
          <section aria-labelledby="ws-presets-heading">
            <div className="flex items-center justify-between mb-2.5">
              <h3 id="ws-presets-heading" className="text-xs font-semibold text-slate-200">
                Presets
              </h3>
              {config.preset === 'custom' && (
                <span className="text-[0.6875rem] text-sky-300">Custom configuration</span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(['focus', 'standard', 'research'] as const).map((presetId) => {
                const preset = WORKSPACE_PRESETS[presetId]
                const active = config.preset === presetId
                return (
                  <button
                    key={presetId}
                    type="button"
                    onClick={() => applyPreset(presetId)}
                    aria-pressed={active}
                    className={`rounded-lg border px-3 py-2.5 text-left transition-colors cursor-pointer ${
                      active
                        ? 'border-sky-500/60 bg-sky-500/15 text-sky-100'
                        : 'border-ink-line bg-ink-soft text-slate-300 hover:border-slate-500 hover:text-slate-100'
                    }`}
                  >
                    <span className="block text-xs font-semibold whitespace-nowrap">{preset.label}</span>
                    <span className="mt-1 block text-[0.6875rem] leading-snug text-slate-400">
                      {presetId === 'focus'
                        ? 'Card only'
                        : presetId === 'standard'
                          ? 'Balanced'
                          : 'All panels'}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>

          {/* 2. Review Workspace Modules */}
          <section aria-labelledby="ws-review-modules-heading" className="border-t border-ink-line pt-5">
            <h3 id="ws-review-modules-heading" className="text-xs font-semibold text-slate-200 mb-3">
              Review Modules
            </h3>
            <div className="space-y-2">
              {REVIEW_MODULE_META.map((mod) => {
                const enabled = config.reviewModules[mod.id]
                return (
                  <div
                    key={mod.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-ink-line bg-ink-soft/70 px-3.5 py-2.5"
                  >
                    <div className="min-w-0">
                      <span className="block text-xs font-medium text-slate-100">{mod.label}</span>
                      <span className="block text-[0.6875rem] text-slate-400">{mod.description}</span>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={enabled}
                      aria-label={`Toggle ${mod.label}`}
                      onClick={() => toggleReviewModule(mod.id)}
                      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors cursor-pointer ${
                        enabled ? 'bg-sky-500' : 'bg-slate-700'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                          enabled ? 'translate-x-4 left-0.5' : 'translate-x-0 left-0.5'
                        }`}
                      />
                    </button>
                  </div>
                )
              })}
            </div>
          </section>

          {/* 3. Dock Position & Canvas Width */}
          <section aria-labelledby="ws-geometry-heading" className="border-t border-ink-line pt-5 space-y-4">
            <h3 id="ws-geometry-heading" className="text-xs font-semibold text-slate-200">
              Layout Geometry
            </h3>

            <div>
              <span className="block text-[0.6875rem] text-slate-400 mb-1.5">
                Concordance &amp; Lexicon Dock
              </span>
              <div className="grid grid-cols-3 gap-1.5 rounded-lg border border-ink-line bg-ink-soft p-1">
                {(['hidden', 'left', 'right'] as LexiconDockSide[]).map((side) => {
                  const active = config.lexiconDockSide === side
                  return (
                    <button
                      key={side}
                      type="button"
                      onClick={() => setLexiconSide(side)}
                      aria-pressed={active}
                      className={`rounded-md py-1.5 text-xs font-medium capitalize transition-colors cursor-pointer ${
                        active
                          ? 'bg-sky-500/20 text-sky-100 border border-sky-500/50'
                          : 'text-slate-400 hover:text-slate-200 border border-transparent'
                      }`}
                    >
                      {side === 'hidden' ? 'Hidden' : side === 'left' ? 'Dock Left' : 'Dock Right'}
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <span className="block text-[0.6875rem] text-slate-400 mb-1.5">Card Reading Width</span>
              <div className="grid grid-cols-3 gap-1.5 rounded-lg border border-ink-line bg-ink-soft p-1">
                {(['compact', 'balanced', 'wide'] as CanvasWidth[]).map((w) => {
                  const active = config.canvasWidth === w
                  return (
                    <button
                      key={w}
                      type="button"
                      onClick={() => setCanvasWidth(w)}
                      aria-pressed={active}
                      className={`rounded-md py-1.5 text-xs font-medium capitalize transition-colors cursor-pointer ${
                        active
                          ? 'bg-sky-500/20 text-sky-100 border border-sky-500/50'
                          : 'text-slate-400 hover:text-slate-200 border border-transparent'
                      }`}
                    >
                      {w}
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <span className="block text-[0.6875rem] text-slate-400 mb-1.5">
                Top Strip Order (Review)
              </span>
              <div className="space-y-1.5">
                {config.reviewTopOrder.map((barId, idx) => {
                  const isEnabled = config.reviewModules[barId]
                  return (
                    <div
                      key={barId}
                      className="flex items-center justify-between rounded-lg border border-ink-line bg-ink-soft/60 px-3 py-2 text-xs"
                    >
                      <span className={isEnabled ? 'text-slate-100 font-medium' : 'text-slate-500'}>
                        {idx + 1}. {TOP_BAR_LABELS[barId]}
                        {!isEnabled && ' (hidden)'}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          disabled={idx === 0}
                          onClick={() => moveTopBar(barId, 'up')}
                          aria-label={`Move ${TOP_BAR_LABELS[barId]} up`}
                          className="rounded border border-ink-line px-2 py-0.5 text-[0.6875rem] text-slate-300 hover:border-slate-500 disabled:opacity-30 cursor-pointer"
                        >
                          Up
                        </button>
                        <button
                          type="button"
                          disabled={idx === config.reviewTopOrder.length - 1}
                          onClick={() => moveTopBar(barId, 'down')}
                          aria-label={`Move ${TOP_BAR_LABELS[barId]} down`}
                          className="rounded border border-ink-line px-2 py-0.5 text-[0.6875rem] text-slate-300 hover:border-slate-500 disabled:opacity-30 cursor-pointer"
                        >
                          Down
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </section>

          {/* 4. Top Navigation Bar Pins */}
          <section aria-labelledby="ws-nav-pins-heading" className="border-t border-ink-line pt-5">
            <h3 id="ws-nav-pins-heading" className="text-xs font-semibold text-slate-200 mb-1">
              Pinned Navigation
            </h3>
            <p className="text-[0.6875rem] text-slate-400 mb-3">
              Choose which workspaces stay in the top bar. Unpinned items remain available under More and Command Search.
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {availableNav.map((route) => {
                const pinned = config.pinnedNavRoutes.includes(route.to)
                const locked = route.to === '/review'
                return (
                  <button
                    key={route.to}
                    type="button"
                    disabled={locked}
                    onClick={() => togglePinnedNav(route.to)}
                    aria-pressed={pinned}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition-colors ${
                      locked
                        ? 'border-sky-500/40 bg-sky-500/10 text-sky-200 cursor-default'
                        : pinned
                          ? 'border-sky-500/50 bg-sky-500/15 text-slate-100 cursor-pointer'
                          : 'border-ink-line bg-ink-soft/60 text-slate-400 hover:border-slate-500 hover:text-slate-200 cursor-pointer'
                    }`}
                  >
                    <span className="truncate font-medium">{route.label}</span>
                    <span className="text-[0.6875rem] shrink-0 ml-2">
                      {locked ? 'Home' : pinned ? 'Pinned' : 'More'}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>

          {/* 5. Code Lab Modules */}
          <section aria-labelledby="ws-codelab-heading" className="border-t border-ink-line pt-5">
            <h3 id="ws-codelab-heading" className="text-xs font-semibold text-slate-200 mb-3">
              Code Lab Modules
            </h3>
            <div className="space-y-2">
              {CODELAB_MODULE_META.map((mod) => {
                const enabled = config.codeLabModules[mod.id]
                return (
                  <div
                    key={mod.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-ink-line bg-ink-soft/70 px-3.5 py-2.5"
                  >
                    <div className="min-w-0">
                      <span className="block text-xs font-medium text-slate-100">{mod.label}</span>
                      <span className="block text-[0.6875rem] text-slate-400">{mod.description}</span>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={enabled}
                      aria-label={`Toggle ${mod.label}`}
                      onClick={() => toggleCodeLabModule(mod.id)}
                      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors cursor-pointer ${
                        enabled ? 'bg-sky-500' : 'bg-slate-700'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                          enabled ? 'translate-x-4 left-0.5' : 'translate-x-0 left-0.5'
                        }`}
                      />
                    </button>
                  </div>
                )
              })}
            </div>
          </section>
        </div>

        <div className="flex items-center justify-between border-t border-ink-line px-5 py-3.5">
          <button
            type="button"
            onClick={resetWorkspace}
            className="rounded-lg border border-ink-line bg-ink-soft px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-slate-500 hover:text-white transition-colors cursor-pointer"
          >
            Reset Defaults
          </button>
          <button
            type="button"
            onClick={() => setCustomizerOpen(false)}
            className="rounded-lg bg-sky-500 px-4 py-1.5 text-xs font-semibold text-slate-950 hover:bg-sky-400 transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </aside>
    </NativeDialog>
  )
}
