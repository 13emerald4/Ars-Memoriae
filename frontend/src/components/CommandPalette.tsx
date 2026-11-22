import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { NativeDialog } from './NativeDialog'
import {
  ALL_NAV_ROUTES,
  CODELAB_MODULE_META,
  REVIEW_MODULE_META,
  WORKSPACE_PRESETS,
  filterCommandItems,
  type CommandItem,
} from '../utils/workspaceModules'
import { useFullscreen } from './FullscreenContext'
import { useLexicon } from './LexiconContext'
import { useWorkspace } from './WorkspaceContext'

interface ExecutableCommand extends CommandItem {
  run: () => void
}

export function CommandPalette() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { openLexicon } = useLexicon()
  const { toggleZenMode, isZenMode } = useFullscreen()
  const {
    config,
    applyPreset,
    toggleReviewModule,
    toggleCodeLabModule,
    setCustomizerOpen,
    commandPaletteOpen,
    setCommandPaletteOpen,
  } = useWorkspace()

  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery('')
      setSelectedIndex(0)
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [commandPaletteOpen])

  const allCommands = useMemo<ExecutableCommand[]>(() => {
    const close = () => setCommandPaletteOpen(false)
    const items: ExecutableCommand[] = []

    for (const route of ALL_NAV_ROUTES) {
      if (route.to === '/code/fundamentals' && user?.show_pre_leetcode === false) continue
      if (route.to === '/code' && user?.show_code_lab === false) continue
      items.push({
        id: `nav:${route.to}`,
        group: 'Navigate',
        label: route.label,
        hint: route.description,
        keywords: [route.to, 'go', 'open', 'page'],
        run: () => {
          navigate(route.to)
          close()
        },
      })
    }

    for (const presetId of ['focus', 'standard', 'research'] as const) {
      const p = WORKSPACE_PRESETS[presetId]
      items.push({
        id: `preset:${presetId}`,
        group: 'Workspace Preset',
        label: `${p.label} Layout`,
        hint: p.tagline,
        active: config.preset === presetId,
        keywords: ['layout', 'preset', 'mode', presetId],
        run: () => {
          applyPreset(presetId)
          close()
        },
      })
    }

    for (const mod of REVIEW_MODULE_META) {
      const on = config.reviewModules[mod.id]
      items.push({
        id: `review-mod:${mod.id}`,
        group: 'Toggle Module',
        label: `${on ? 'Hide' : 'Show'} ${mod.label}`,
        hint: mod.description,
        active: on,
        keywords: ['toggle', 'review', 'module', mod.id],
        run: () => {
          toggleReviewModule(mod.id)
          close()
        },
      })
    }

    for (const mod of CODELAB_MODULE_META) {
      const on = config.codeLabModules[mod.id]
      items.push({
        id: `code-mod:${mod.id}`,
        group: 'Toggle Module',
        label: `${on ? 'Hide' : 'Show'} Code Lab ${mod.label}`,
        hint: mod.description,
        active: on,
        keywords: ['toggle', 'code', 'lab', 'module', mod.id],
        run: () => {
          toggleCodeLabModule(mod.id)
          close()
        },
      })
    }

    items.push(
      {
        id: 'action:customizer',
        group: 'Action',
        label: 'Customize Workspace Layout',
        hint: 'Reorder strips, dock panels, and pin navigation items',
        keywords: ['layout', 'modules', 'settings', 'drawer'],
        run: () => {
          close()
          setCustomizerOpen(true)
        },
      },
      {
        id: 'action:lexicon',
        group: 'Action',
        label: 'Open Lexicon Lookup',
        hint: 'Search definitions and study terminology',
        keywords: ['dictionary', 'glossary', 'terms'],
        run: () => {
          close()
          openLexicon()
        },
      },
      {
        id: 'action:zen',
        group: 'Action',
        label: isZenMode ? 'Exit Zen Mode' : 'Enter Zen Mode',
        hint: 'Auto-hide the top navigation bar while studying',
        keywords: ['fullscreen', 'focus', 'hide header'],
        run: () => {
          toggleZenMode()
          close()
        },
      },
    )

    return items
  }, [
    user?.show_pre_leetcode,
    user?.show_code_lab,
    config.preset,
    config.reviewModules,
    config.codeLabModules,
    isZenMode,
    navigate,
    applyPreset,
    toggleReviewModule,
    toggleCodeLabModule,
    setCustomizerOpen,
    setCommandPaletteOpen,
    openLexicon,
    toggleZenMode,
  ])

  const filtered = useMemo(
    () => filterCommandItems(allCommands, deferredQuery),
    [allCommands, deferredQuery],
  )

  useEffect(() => {
    setSelectedIndex(0)
  }, [deferredQuery])

  if (!commandPaletteOpen) return null

  const executeSelected = () => {
    const target = filtered[selectedIndex]
    if (target) target.run()
  }

  return (
    <NativeDialog
      open={commandPaletteOpen}
      onClose={() => setCommandPaletteOpen(false)}
      ariaLabel="Command palette"
      variant="palette"
      className="w-full max-w-xl"
    >
      <div className="w-full overflow-hidden rounded-xl border border-ink-line bg-ink shadow-2xl outline-none">
        <div className="flex items-center gap-2.5 border-b border-ink-line px-4 py-3">
          <svg
            className="h-4 w-4 shrink-0 text-slate-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setSelectedIndex((i) => Math.min(filtered.length - 1, i + 1))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setSelectedIndex((i) => Math.max(0, i - 1))
              } else if (e.key === 'Enter') {
                e.preventDefault()
                executeSelected()
              }
            }}
            placeholder="Jump to workspace, switch layout preset, or toggle a module…"
            aria-label="Search commands"
            className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(false)}
            className="rounded border border-ink-line px-1.5 py-0.5 text-[0.6875rem] text-slate-400 hover:text-slate-200 cursor-pointer"
          >
            Esc
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto p-2 scroll-stable" role="listbox" aria-label="Commands">
          {filtered.length === 0 ? (
            <p className="px-3 py-8 text-center text-xs text-slate-400">
              No matching workspaces or modules for &ldquo;{query}&rdquo;.
            </p>
          ) : (
            filtered.map((item, idx) => {
              const selected = idx === selectedIndex
              return (
                <button
                  key={item.id}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  onClick={item.run}
                  className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left transition-colors cursor-pointer ${
                    selected ? 'bg-sky-500/15 text-slate-100' : 'text-slate-300 hover:bg-ink-soft'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium truncate">{item.label}</span>
                      {item.active && (
                        <span className="text-[0.6875rem] text-sky-300">Active</span>
                      )}
                    </div>
                    {item.hint && (
                      <p className="truncate text-[0.6875rem] text-slate-400">{item.hint}</p>
                    )}
                  </div>
                  <span className="shrink-0 text-[0.6875rem] text-slate-500">{item.group}</span>
                </button>
              )
            })
          )}
        </div>

        <div className="flex items-center justify-between border-t border-ink-line px-4 py-2 text-[0.6875rem] text-slate-500">
          <span>Use Up/Down and Enter to run</span>
          <span>Ctrl/Cmd + K</span>
        </div>
      </div>
    </NativeDialog>
  )
}
