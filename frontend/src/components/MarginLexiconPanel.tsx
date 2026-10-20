import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { api } from '../api/client'
import type { LexiconEntry, LexiconGlossItem, RecentLexiconItem } from '../api/types'
import {
  resolveConcordanceEntry,
  findConcordanceMatch,
  type ConcordanceEntry,
} from '../services/concordance_engine'
import { useLexicon } from './LexiconContext'

export interface MarginLexiconPanelProps {
  cardId?: string | null
  deckName?: string | null
  thematicNature?: string | null
  cardFront?: string | null
  cardBack?: string | null
  initialGlosses?: LexiconGlossItem[]
  onGlossesUpdated?: (glosses: LexiconGlossItem[]) => void
}

export function MarginLexiconPanel({
  cardId,
  deckName,
  thematicNature,
  cardFront,
  cardBack,
  initialGlosses,
  onGlossesUpdated,
}: MarginLexiconPanelProps) {
  const { registerMarginListener } = useLexicon()

  // Saved glosses for current card
  const [glosses, setGlosses] = useState<LexiconGlossItem[]>(() => initialGlosses || [])
  const [saving, setSaving] = useState(false)
  const [savedNotice, setSavedNotice] = useState<string | null>(null)

  // Recent lookups from backend session
  const [recentLookups, setRecentLookups] = useState<RecentLexiconItem[]>([])
  const [loadingRecent, setLoadingRecent] = useState(false)

  // Active lookup / search in margin
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [activeEntry, setActiveEntry] = useState<LexiconEntry | null>(null)
  const [activeConcordance, setActiveConcordance] = useState<ConcordanceEntry | null>(null)
  const [lookupError, setLookupError] = useState<string | null>(null)

  // UI tabs & collapse state
  const [activeTab, setActiveTab] = useState<'card_glosses' | 'lookup' | 'recent'>('card_glosses')
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('memorization.marginLexiconCollapsed') === 'true'
    } catch {
      return false
    }
  })

  // Synchronize when active card changes
  const prevCardIdRef = useRef<string | null | undefined>(cardId)
  useEffect(() => {
    if (cardId !== prevCardIdRef.current) {
      prevCardIdRef.current = cardId
      setGlosses(initialGlosses || [])
      setActiveEntry(null)
      setActiveConcordance(null)
      setQuery('')
      setLookupError(null)
      setSavedNotice(null)
      // Default to card_glosses if card has glosses, otherwise keep active tab
      if ((initialGlosses || []).length > 0) {
        setActiveTab('card_glosses')
      }
    } else if (initialGlosses && initialGlosses !== glosses) {
      // Prop updated from outside
      setGlosses(initialGlosses)
    }
  }, [cardId, initialGlosses])

  // Fetch recent lookups
  const refreshRecent = useCallback(async () => {
    setLoadingRecent(true)
    try {
      const items = await api.getRecentLexicon()
      setRecentLookups(items)
    } catch {
      // non-fatal
    } finally {
      setLoadingRecent(false)
    }
  }, [])

  useEffect(() => {
    void refreshRecent()
  }, [refreshRecent])

  // Persist glosses to backend card
  const persistGlosses = useCallback(
    async (nextGlosses: LexiconGlossItem[], noticeText?: string) => {
      setGlosses(nextGlosses)
      onGlossesUpdated?.(nextGlosses)
      if (!cardId) return

      setSaving(true)
      try {
        await api.updateCardLexiconGlosses(cardId, nextGlosses)
        setSavedNotice(noticeText || 'Saved to card memory')
        setTimeout(() => setSavedNotice(null), 3000)
      } catch (err) {
        console.error('Failed to update card lexicon glosses:', err)
        setSavedNotice('Failed to save to card')
        setTimeout(() => setSavedNotice(null), 4000)
      } finally {
        setSaving(false)
      }
    },
    [cardId, onGlossesUpdated],
  )

  // Perform lookup for a given term (concordance + AI/lexicon)
  const handleLookup = useCallback(
    async (termToLookup: string, lookupContext?: string | null) => {
      const trimmed = termToLookup.trim()
      if (!trimmed) return

      setSearching(true)
      setLookupError(null)
      setActiveTab('lookup')

      // Check local concordance engine first for instant definition
      const matched = resolveConcordanceEntry(trimmed) || findConcordanceMatch(trimmed)
      setActiveConcordance(matched)

      // Fall back to card front & back text if lookupContext not explicitly provided
      const cardContextSnippet = cardFront || cardBack ? `Front: ${cardFront || ''} | Back: ${cardBack || ''}`.trim() : null
      const effectiveContext = lookupContext || cardContextSnippet

      try {
        const res = await api.lookupLexicon(trimmed, effectiveContext || null, cardId || null, {
          deckName: deckName || null,
          thematicNature: thematicNature || null,
        })
        setActiveEntry(res)
        void refreshRecent()
      } catch (err) {
        if (!matched) {
          setLookupError(err instanceof Error ? err.message : 'Lookup failed')
          setActiveEntry(null)
        }
      } finally {
        setSearching(false)
      }
    },
    [cardId, deckName, thematicNature, cardFront, cardBack, refreshRecent],
  )

  // Register with LexiconContext so text selection / Alt+Click in Review route here
  useEffect(() => {
    registerMarginListener((term, ctx) => {
      setQuery(term)
      void handleLookup(term, ctx)
    })
    return () => {
      registerMarginListener(null)
    }
  }, [registerMarginListener, handleLookup])

  // Compute unpinned recent lookups
  const unpinnedRecent = useMemo(() => {
    const existingTerms = new Set(glosses.map((g) => g.term.toLowerCase().trim()))
    return recentLookups.filter((r) => !existingTerms.has(r.term.toLowerCase().trim()))
  }, [glosses, recentLookups])

  // Populate from all unpinned recent lookups
  const handlePopulateFromRecent = useCallback(() => {
    if (unpinnedRecent.length === 0) return
    const newItems: LexiconGlossItem[] = unpinnedRecent.map((r) => ({
      term: r.term,
      definition: r.definition,
      domain: r.domain || undefined,
      source: 'Recent Lookups',
      pinned_at: new Date().toISOString(),
    }))
    const next = [...glosses, ...newItems]
    void persistGlosses(next, `⚡ Populated ${newItems.length} definition${newItems.length > 1 ? 's' : ''} to card memory`)
    setActiveTab('card_glosses')
  }, [unpinnedRecent, glosses, persistGlosses])

  // Pin a single item
  const handlePinItem = useCallback(
    (item: { term: string; definition: string; domain?: string | null; context_explanation?: string | null; example?: string | null; source?: string }) => {
      const exists = glosses.some((g) => g.term.toLowerCase().trim() === item.term.toLowerCase().trim())
      if (exists) return

      const newGloss: LexiconGlossItem = {
        term: item.term,
        definition: item.definition,
        domain: item.domain || undefined,
        context_explanation: item.context_explanation || undefined,
        example: item.example || undefined,
        source: item.source || 'Concordance & Lexicon',
        pinned_at: new Date().toISOString(),
      }
      const next = [newGloss, ...glosses]
      void persistGlosses(next, `Pinned "${item.term}" to card`)
    },
    [glosses, persistGlosses],
  )

  // Unpin / remove a gloss
  const handleRemoveGloss = useCallback(
    (termToRemove: string) => {
      const next = glosses.filter((g) => g.term.toLowerCase() !== termToRemove.toLowerCase())
      void persistGlosses(next, `Removed "${termToRemove}" from card`)
    },
    [glosses, persistGlosses],
  )

  // Check if current active entry or concordance is already pinned
  const isCurrentLookupPinned = useMemo(() => {
    const currentTerm = (activeEntry?.term || activeConcordance?.term || '').toLowerCase().trim()
    if (!currentTerm) return false
    return glosses.some((g) => g.term.toLowerCase().trim() === currentTerm)
  }, [activeEntry, activeConcordance, glosses])

  const toggleCollapse = () => {
    const next = !collapsed
    setCollapsed(next)
    try {
      localStorage.setItem('memorization.marginLexiconCollapsed', String(next))
    } catch {}
  }

  return (
    <div className="w-full rounded-2xl border border-sky-500/25 bg-[#0b101b]/95 shadow-xl backdrop-blur-md text-slate-100 font-sans overflow-hidden transition-all duration-200">
      {/* Header Bar */}
      <div className="px-3.5 py-2.5 bg-gradient-to-r from-sky-950/80 via-slate-900 to-indigo-950/60 border-b border-sky-500/20 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
          <h3 className="text-xs font-bold text-sky-200 tracking-wide uppercase truncate">
            Concordance &amp; Lexicon
          </h3>
          {glosses.length > 0 && (
            <span className="rounded-full bg-sky-500/20 border border-sky-400/40 px-2 py-0.2 text-[10px] font-semibold text-sky-300">
              {glosses.length} pinned
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {saving && (
            <span className="text-[10px] text-sky-300 animate-pulse flex items-center gap-1">
              <span className="inline-block h-2 w-2 animate-spin rounded-full border border-sky-400 border-t-transparent" />
              Saving…
            </span>
          )}
          {savedNotice && !saving && (
            <span className="text-[10px] text-emerald-300 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/40 animate-in fade-in duration-150">
              {savedNotice}
            </span>
          )}
          <button
            type="button"
            onClick={toggleCollapse}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 text-xs transition"
            title={collapsed ? 'Expand panel' : 'Collapse panel'}
          >
            {collapsed ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="p-3 space-y-3">
          {/* Quick Search Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (query.trim()) {
                void handleLookup(query.trim())
              }
            }}
            className="relative"
          >
            <input
              type="text"
              placeholder="Search word or concept in margin…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-lg border border-sky-500/25 bg-slate-900/90 pl-3 pr-8 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-400 shadow-inner"
            />
            <button
              type="submit"
              disabled={searching}
              className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 text-xs text-slate-400 hover:text-sky-300 hover:bg-sky-950/50 transition"
              title="Lookup term"
            >
              {searching ? (
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
              ) : (
                '↵'
              )}
            </button>
          </form>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1 border-b border-slate-800 pb-1.5 text-[11px] font-medium text-slate-400">
            <button
              type="button"
              onClick={() => setActiveTab('card_glosses')}
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 ${
                activeTab === 'card_glosses'
                  ? 'bg-sky-950/90 text-sky-200 font-semibold border border-sky-500/40 shadow-sm'
                  : 'hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <span>Card Memory</span>
              {glosses.length > 0 && (
                <span className="rounded-full bg-sky-500/30 px-1.5 py-0.2 text-[9px] text-sky-200">
                  {glosses.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('lookup')}
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 ${
                activeTab === 'lookup'
                  ? 'bg-sky-950/90 text-sky-200 font-semibold border border-sky-500/40 shadow-sm'
                  : 'hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <span>Lookup</span>
              {(activeEntry || activeConcordance) && (
                <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                setActiveTab('recent')
                void refreshRecent()
              }}
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 ${
                activeTab === 'recent'
                  ? 'bg-sky-950/90 text-sky-200 font-semibold border border-sky-500/40 shadow-sm'
                  : 'hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <span>Recent</span>
              {unpinnedRecent.length > 0 && (
                <span className="rounded-full bg-amber-500/30 text-amber-300 px-1.5 py-0.2 text-[9px] font-bold">
                  +{unpinnedRecent.length}
                </span>
              )}
            </button>
          </div>

          {/* Quick Populate Banner when there are unpinned recent terms */}
          {unpinnedRecent.length > 0 && activeTab !== 'recent' && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-950/25 p-2.5 flex items-center justify-between gap-2 text-xs">
              <div className="min-w-0">
                <p className="font-semibold text-amber-200 truncate">
                  ⚡ {unpinnedRecent.length} Recent Lookup{unpinnedRecent.length > 1 ? 's' : ''}
                </p>
                <p className="text-[10px] text-amber-300/80 truncate">
                  {unpinnedRecent.map((r) => r.term).slice(0, 3).join(', ')}
                  {unpinnedRecent.length > 3 ? '…' : ''}
                </p>
              </div>
              <button
                type="button"
                onClick={handlePopulateFromRecent}
                className="shrink-0 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/40 px-2.5 py-1 text-[11px] font-semibold text-amber-200 hover:text-white transition shadow-sm"
                title="Populate this card's memory with recent lookups"
              >
                + Populate All
              </button>
            </div>
          )}

          {/* TAB 1: CARD MEMORY & MARGINALIA */}
          {activeTab === 'card_glosses' && (
            <div className="space-y-2.5 max-h-[520px] overflow-y-auto pr-1">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[10px] text-sky-300">
                  Card Glosses ({glosses.length})
                </span>
                <span className="text-[10px] text-slate-500 italic">
                  Persists across all reviews
                </span>
              </div>

              {glosses.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700/60 bg-slate-900/30 p-4 text-center space-y-2">
                  <p className="text-xs text-slate-300 font-medium">No definitions pinned yet</p>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Highlight any word, Alt+Click, or search above to attach definitions that will automatically appear every time you review this card.
                  </p>
                  {unpinnedRecent.length > 0 && (
                    <button
                      type="button"
                      onClick={handlePopulateFromRecent}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-sky-400/50 bg-sky-950/80 px-3 py-1 text-xs font-semibold text-sky-200 hover:bg-sky-900 transition"
                    >
                      ⚡ Populate {unpinnedRecent.length} Recent Lookup{unpinnedRecent.length > 1 ? 's' : ''}
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {glosses.map((item, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-sky-500/20 bg-slate-900/80 p-2.5 space-y-1.5 shadow-sm hover:border-sky-400/40 transition group"
                    >
                      <div className="flex items-baseline justify-between gap-1.5">
                        <div className="flex items-baseline gap-1.5 flex-wrap min-w-0">
                          <h4 className="text-xs font-bold text-sky-200 capitalize">
                            {item.term}
                          </h4>
                          {item.domain && (
                            <span className="text-[9px] font-semibold text-slate-400 bg-slate-800 px-1.5 py-0.2 rounded border border-slate-700/60">
                              {item.domain}
                            </span>
                          )}
                          {item.source && (
                            <span className="text-[9px] text-sky-400/70">
                              {item.source}
                            </span>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveGloss(item.term)}
                          className="opacity-60 group-hover:opacity-100 text-slate-400 hover:text-rose-400 hover:bg-rose-950/50 rounded px-1.5 py-0.5 text-xs transition"
                          title="Remove from card memory"
                        >
                          &times;
                        </button>
                      </div>

                      <p className="text-xs text-slate-200 leading-relaxed">
                        {item.definition}
                      </p>

                      {item.definitions && item.definitions.length > 0 && (
                        <ul className="text-xs text-slate-300 space-y-1 list-disc pl-4 mt-1">
                          {item.definitions.map((d, dIdx) => (
                            <li key={dIdx} className="leading-snug">{d}</li>
                          ))}
                        </ul>
                      )}

                      {item.context_explanation && (
                        <p className="text-[11px] text-sky-300/80 bg-sky-950/40 rounded p-1.5 border border-sky-500/15 leading-snug">
                          {item.context_explanation}
                        </p>
                      )}

                      {item.example && (
                        <pre className="text-[10px] font-mono text-emerald-300 bg-slate-950/80 p-1.5 rounded overflow-x-auto whitespace-pre-wrap">
                          {item.example}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: ACTIVE LOOKUP */}
          {activeTab === 'lookup' && (
            <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
              {searching ? (
                <div className="py-8 text-center space-y-2">
                  <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
                  <p className="text-xs text-slate-400">Consulting concordance &amp; AI lexicon…</p>
                </div>
              ) : lookupError && !activeConcordance ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-200 space-y-1">
                  <p className="font-semibold">Lookup not found</p>
                  <p className="text-[11px] text-rose-300/80">{lookupError}</p>
                </div>
              ) : activeEntry || activeConcordance ? (
                <div className="space-y-3">
                  {/* Title & Pin Button */}
                  <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
                    <div className="min-w-0">
                      <h4 className="text-sm font-bold text-sky-200 capitalize truncate">
                        {activeEntry?.term || activeConcordance?.term}
                      </h4>
                      <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                        {activeEntry?.domain && (
                          <span className="rounded bg-sky-950/80 px-1.5 py-0.2 border border-sky-500/30 text-sky-300">
                            {activeEntry.domain}
                          </span>
                        )}
                        {activeConcordance && (
                          <span className="rounded bg-indigo-950/80 px-1.5 py-0.2 border border-indigo-500/30 text-indigo-300">
                            {activeConcordance.category}
                          </span>
                        )}
                        {activeEntry?.cached && (
                          <span className="text-emerald-400">cached</span>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        const term = activeEntry?.term || activeConcordance?.term || ''
                        const def = activeEntry?.definition || activeConcordance?.definition || ''
                        if (isCurrentLookupPinned) {
                          handleRemoveGloss(term)
                        } else {
                          handlePinItem({
                            term,
                            definition: def,
                            domain: activeEntry?.domain || activeConcordance?.category || undefined,
                            context_explanation: activeEntry?.context_explanation || undefined,
                            example: activeEntry?.example || activeConcordance?.leetCodeRelevance || undefined,
                            source: activeConcordance ? 'MIT Concordance' : 'AI Lexicon',
                          })
                        }
                      }}
                      className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-semibold transition shadow-sm ${
                        isCurrentLookupPinned
                          ? 'border border-emerald-500/50 bg-emerald-950/60 text-emerald-200 hover:bg-rose-950/60 hover:border-rose-500/50 hover:text-rose-200'
                          : 'border border-sky-400/50 bg-sky-950/80 text-sky-200 hover:bg-sky-900 hover:border-sky-300'
                      }`}
                    >
                      {isCurrentLookupPinned ? '✓ Pinned (Click to Unpin)' : '📌 Pin to Card'}
                    </button>
                  </div>

                  {/* Definition Box */}
                  <div className="rounded-xl border border-sky-500/20 bg-sky-950/30 p-2.5 space-y-1">
                    <p className="text-[10px] font-semibold text-sky-300 uppercase tracking-wider">
                      Definition
                    </p>
                    <p className="text-xs leading-relaxed text-slate-100">
                      {activeEntry?.definition || activeConcordance?.definition}
                    </p>
                  </div>

                  {/* Context explanation if present */}
                  {activeEntry?.context_explanation && (
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                        Relevance to this Card
                      </p>
                      <p className="text-xs leading-relaxed text-slate-300 bg-slate-900/60 rounded-lg p-2 border border-ink-line/40">
                        {activeEntry.context_explanation}
                      </p>
                    </div>
                  )}

                  {/* Concrete example / code */}
                  {(activeEntry?.example || activeConcordance?.notation) && (
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold text-amber-300/90 uppercase tracking-wider">
                        Example / Notation
                      </p>
                      <pre className="text-[10px] font-mono text-emerald-300 bg-slate-950/90 p-2 rounded-lg border border-ink-line/50 overflow-x-auto whitespace-pre-wrap">
                        {activeEntry?.example || activeConcordance?.notation}
                      </pre>
                    </div>
                  )}

                  {/* Related terms */}
                  {activeEntry?.related_terms && activeEntry.related_terms.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                        Related Concepts
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {activeEntry.related_terms.map((rt, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => {
                              setQuery(rt)
                              void handleLookup(rt)
                            }}
                            className="rounded-md border border-slate-700/60 bg-slate-800/60 px-2 py-0.5 text-[11px] text-sky-200 hover:border-sky-400 hover:bg-sky-900/40 transition"
                          >
                            + {rt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-slate-400 space-y-1.5">
                  <p>Type a word above or select text anywhere on the card to look up its definition.</p>
                  <p className="text-[10px] text-slate-500">
                    Results appear here and can be pinned with one click.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: RECENT LOOKUPS */}
          {activeTab === 'recent' && (
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[10px]">
                  Recent Lookups ({recentLookups.length})
                </span>
                {unpinnedRecent.length > 0 && (
                  <button
                    type="button"
                    onClick={handlePopulateFromRecent}
                    className="text-amber-300 hover:text-amber-100 font-semibold underline text-[10px]"
                  >
                    Pin All ({unpinnedRecent.length})
                  </button>
                )}
              </div>

              {loadingRecent ? (
                <p className="text-xs text-slate-500 italic py-4 text-center">Loading recent lookups…</p>
              ) : recentLookups.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-4 text-center">No recent lookups yet.</p>
              ) : (
                <div className="space-y-1.5">
                  {recentLookups.map((rt, idx) => {
                    const isPinned = glosses.some(
                      (g) => g.term.toLowerCase().trim() === rt.term.toLowerCase().trim(),
                    )
                    return (
                      <div
                        key={idx}
                        className="rounded-xl border border-ink-line/40 bg-slate-900/50 p-2 hover:bg-slate-800/80 hover:border-sky-500/40 transition group"
                      >
                        <div className="flex items-center justify-between gap-1 text-xs font-semibold">
                          <button
                            type="button"
                            onClick={() => {
                              setQuery(rt.term)
                              void handleLookup(rt.term)
                            }}
                            className="text-left text-sky-200 hover:text-sky-300 truncate"
                          >
                            {rt.term}
                          </button>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {rt.domain && (
                              <span className="text-[9px] text-slate-400">{rt.domain}</span>
                            )}
                            <button
                              type="button"
                              onClick={() => {
                                if (isPinned) {
                                  handleRemoveGloss(rt.term)
                                } else {
                                  handlePinItem({
                                    term: rt.term,
                                    definition: rt.definition,
                                    domain: rt.domain,
                                    source: 'Recent Lookups',
                                  })
                                }
                              }}
                              className={`rounded px-1.5 py-0.5 text-[10px] font-semibold transition ${
                                isPinned
                                  ? 'text-emerald-300 bg-emerald-950/60 border border-emerald-500/40 hover:text-rose-300'
                                  : 'text-sky-300 bg-sky-950/60 border border-sky-500/40 hover:bg-sky-900 hover:text-white'
                              }`}
                            >
                              {isPinned ? '✓ Pinned' : '+ Pin'}
                            </button>
                          </div>
                        </div>
                        <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">
                          {rt.definition}
                        </p>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Footer note */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
            <span>Alt+Click word to define in margin</span>
            <span>💾 Auto-synced</span>
          </div>
        </div>
      )}
    </div>
  )
}
