import { useEffect, useRef, useState, useCallback } from 'react'
import { api } from '../api/client'
import type { LexiconEntry, RecentLexiconItem } from '../api/types'

interface LexiconPopoverProps {
  term: string | null
  context?: string | null
  position?: { x: number; y: number } | null
  onClose: () => void
  onLookupNewTerm?: (newTerm: string) => void
}

export function LexiconPopover({
  term: initialTerm,
  context,
  position,
  onClose,
  onLookupNewTerm,
}: LexiconPopoverProps) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [entry, setEntry] = useState<LexiconEntry | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [recentTerms, setRecentTerms] = useState<RecentLexiconItem[]>([])
  const [showRecent, setShowRecent] = useState(false)
  const popoverRef = useRef<HTMLDivElement>(null)

  const doLookup = useCallback(async (lookupWord: string) => {
    if (!lookupWord.trim()) return
    setLoading(true)
    setError(null)
    setShowRecent(false)
    try {
      const res = await api.lookupLexicon(lookupWord.trim(), context)
      setEntry(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lookup failed')
      setEntry(null)
    } finally {
      setLoading(false)
    }
  }, [context])

  useEffect(() => {
    if (initialTerm) {
      void doLookup(initialTerm)
    }
  }, [initialTerm, doLookup])

  useEffect(() => {
    // Fetch recent items for concordance
    api.getRecentLexicon().then(setRecentTerms).catch(() => {})
  }, [entry])

  // Handle outside click & escape key
  useEffect(() => {
    let ready = false
    const timer = setTimeout(() => {
      ready = true
    }, 150)

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    function handleClickOutside(e: MouseEvent) {
      if (!ready) return
      const target = e.target as HTMLElement | null
      if (target && target.closest('[data-lexicon-trigger="true"]')) {
        return
      }
      if (popoverRef.current && !popoverRef.current.contains(target as Node)) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])

  // Calculate popover positioning within window bounds
  const top = position ? Math.min(window.innerHeight - 440, Math.max(20, position.y + 12)) : Math.max(60, window.innerHeight / 2 - 220)
  const left = position ? Math.min(window.innerWidth - 440, Math.max(20, position.x - 180)) : Math.max(20, window.innerWidth / 2 - 200)

  return (
    <div
      ref={popoverRef}
      style={{
        position: 'fixed',
        top: `${top}px`,
        left: `${left}px`,
        zIndex: 9999,
      }}
      className="w-[420px] max-w-[94vw] rounded-2xl border border-sky-500/30 bg-[#0d131f]/95 p-4 shadow-2xl backdrop-blur-md transition-all duration-150 animate-in fade-in zoom-in-95 text-slate-100 font-sans"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-ink-line/60 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold text-sky-300 flex items-center gap-1.5">
            Concordance &amp; Lexicon
          </span>
          {entry?.domain && (
            <span className="rounded-full bg-sky-950/80 border border-sky-500/30 px-2 py-0.5 text-[10px] font-medium text-sky-200">
              {entry.domain}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowRecent(!showRecent)}
            className="text-[11px] text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded hover:bg-slate-800 transition-colors"
            title="View recent lookups"
          >
            {showRecent ? 'Definition' : 'Recent'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-sm font-semibold p-1 hover:bg-slate-800/80 rounded transition-colors"
          >
            &times;
          </button>
        </div>
      </div>

      {/* Quick Search Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (query.trim()) {
            void doLookup(query.trim())
            onLookupNewTerm?.(query.trim())
            setQuery('')
          }
        }}
        className="mb-3"
      >
        <div className="relative">
          <input
            type="text"
            placeholder="Search word or concept in lexicon…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-lg border border-ink-line bg-slate-900/90 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-400"
          />
          <button
            type="submit"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-sky-300 text-xs px-2 py-0.5"
          >
            ↵
          </button>
        </div>
      </form>

      {/* Main Content Area */}
      {showRecent ? (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Recently Looked Up Terms
          </p>
          {recentTerms.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-4 text-center">No recent terms yet.</p>
          ) : (
            recentTerms.map((rt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => doLookup(rt.term)}
                className="w-full text-left rounded-lg border border-ink-line/40 bg-slate-900/50 p-2 hover:bg-slate-800/80 hover:border-sky-500/40 transition-colors group"
              >
                <div className="flex items-center justify-between text-xs font-semibold text-sky-200 group-hover:text-sky-300">
                  <span>{rt.term}</span>
                  {rt.domain && <span className="text-[10px] text-slate-400">{rt.domain}</span>}
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{rt.definition}</p>
              </button>
            ))
          )}
        </div>
      ) : loading ? (
        <div className="py-8 text-center space-y-2">
          <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
          <p className="text-xs text-slate-400">Consulting AI technical concordance…</p>
        </div>
      ) : error ? (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
          <p className="font-semibold">Unable to fetch definition</p>
          <p className="text-[11px] text-rose-300/80 mt-1">{error}</p>
        </div>
      ) : entry ? (
        <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
          {/* Term Title & Cache Chip */}
          <div className="flex items-baseline justify-between">
            <h3 className="text-base font-bold text-sky-200 capitalize tracking-tight">
              {entry.term}
            </h3>
            {entry.cached && (
              <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                instant cache
              </span>
            )}
          </div>

          {/* Core Definition */}
          <div className="rounded-lg border border-sky-500/20 bg-sky-950/30 p-2.5">
            <p className="text-[10px] font-semibold text-sky-300 uppercase tracking-wider mb-1">
              Definition
            </p>
            <p className="text-xs leading-relaxed text-slate-200 font-medium">
              {entry.definition}
            </p>
          </div>

          {/* Context Explanation */}
          {entry.context_explanation && (
            <div className="space-y-1">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Why It Matters Here
              </p>
              <p className="text-xs leading-relaxed text-slate-300">
                {entry.context_explanation}
              </p>
            </div>
          )}

          {/* Code / Concrete Example */}
          {entry.example && (
            <div className="rounded-lg border border-ink-line bg-slate-950/80 p-2 text-xs">
              <p className="text-[10px] font-semibold text-amber-300/90 uppercase tracking-wider mb-1">
                Concrete Example
              </p>
              <code className="block font-mono text-[11px] text-emerald-300 bg-slate-900 px-2 py-1.5 rounded overflow-x-auto whitespace-pre-wrap">
                {entry.example}
              </code>
            </div>
          )}

          {/* Related Terms / Concordance Navigation */}
          {entry.related_terms && entry.related_terms.length > 0 && (
            <div className="pt-2 border-t border-ink-line/50">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Related Concepts (Click to explore)
              </p>
              <div className="flex flex-wrap gap-1.5">
                {entry.related_terms.map((rt, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => {
                      void doLookup(rt)
                      onLookupNewTerm?.(rt)
                    }}
                    className="rounded-md border border-slate-700/60 bg-slate-800/60 px-2 py-0.5 text-[11px] text-sky-200 hover:border-sky-400 hover:bg-sky-900/40 transition-colors"
                  >
                    + {rt}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="py-4 text-center text-xs text-slate-400">
          Click any word or type in the search bar above to look up its definition.
        </div>
      )}

      {/* Footer hint */}
      <div className="mt-3 pt-2 border-t border-ink-line/40 flex items-center justify-between text-[10px] text-slate-500">
        <span>Tip: Highlight any phrase in text to define it</span>
        <span>Esc to close</span>
      </div>
    </div>
  )
}
