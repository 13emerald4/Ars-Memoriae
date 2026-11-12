import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { api } from '../api/client'
import type { LexiconEntry, LexiconGlossItem, RecentLexiconItem } from '../api/types'
import {
  resolveConcordanceEntry,
  findConcordanceMatch,
  loadConcordanceLexicon,
  type ConcordanceEntry,
} from '../services/concordance_engine'
import { useLexicon } from './LexiconContext'
import { AddToDefinitionsPrompt } from './AddToDefinitionsPrompt'
import { canonicalTermKey, isTermInGlosses, looksLikeCodeTerm } from '../utils/lexiconExtractor'

function renderInlineBackticks(text?: string | null) {
  if (!text) return null
  const parts = text.split(/(`[^`]+`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={i}
          className="px-1 py-0.2 rounded bg-emerald-950/70 text-emerald-300 font-mono text-[11px] border border-emerald-500/20 mx-0.5"
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    return <span key={i}>{part}</span>
  })
}

export interface MarginLexiconPanelProps {
  cardId?: string | null
  deckId?: string | null
  deckName?: string | null
  thematicNature?: string | null
  cardFront?: string | null
  cardBack?: string | null
  initialGlosses?: LexiconGlossItem[]
  onGlossesUpdated?: (glosses: LexiconGlossItem[]) => void
  onLookupTriggered?: () => void
  collapsedRailOnDesktop?: boolean
  onCollapseChange?: (collapsed: boolean) => void
  codeLanguage?: string
  embedded?: boolean
}

export function MarginLexiconPanel({
  cardId,
  deckId,
  deckName,
  thematicNature,
  cardFront,
  cardBack,
  initialGlosses,
  onGlossesUpdated,
  onLookupTriggered,
  collapsedRailOnDesktop = false,
  onCollapseChange,
  codeLanguage = 'typescript',
  embedded = false,
}: MarginLexiconPanelProps) {
  const { registerMarginListener, registerPopulateListener, populateCardGlosses, syncCardGlosses } =
    useLexicon()
  const onLookupTriggeredRef = useRef(onLookupTriggered)
  onLookupTriggeredRef.current = onLookupTriggered

  // Saved glosses for current card
  const [glosses, setGlosses] = useState<LexiconGlossItem[]>(() => initialGlosses || [])
  const glossesRef = useRef<LexiconGlossItem[]>(glosses)
  glossesRef.current = glosses
  const [saving, setSaving] = useState(false)
  const [extractingTerms, setExtractingTerms] = useState(false)
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
  const [dismissedPromptKey, setDismissedPromptKey] = useState<string | null>(null)

  // UI tabs & collapse state
  const [activeTab, setActiveTab] = useState<'card_glosses' | 'lookup' | 'recent'>('card_glosses')
  const [collapsed, setCollapsed] = useState(() => {
    if ((initialGlosses || []).length > 0) {
      return false
    }
    try {
      return localStorage.getItem('memorization.marginLexiconCollapsed') === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    onCollapseChange?.(collapsed)
  }, [collapsed, onCollapseChange])

  // Synchronize when active card changes or initialGlosses populate
  const prevCardIdRef = useRef<string | null | undefined>(cardId)
  const prevInitialGlossesRef = useRef<LexiconGlossItem[] | undefined>(initialGlosses)
  useEffect(() => {
    const cardChanged = cardId !== prevCardIdRef.current
    const glossesChanged = initialGlosses !== prevInitialGlossesRef.current
    if (cardChanged) {
      prevCardIdRef.current = cardId
      prevInitialGlossesRef.current = initialGlosses
      const next = initialGlosses || []
      setGlosses(next)
      syncCardGlosses(cardId, next)
      setActiveEntry(null)
      setActiveConcordance(null)
      setQuery('')
      setLookupError(null)
      setSavedNotice(null)
      setDismissedPromptKey(null)
      if (next.length > 0) {
        setActiveTab('card_glosses')
        setCollapsed(false)
      }
    } else if (glossesChanged) {
      prevInitialGlossesRef.current = initialGlosses
      const next = initialGlosses || []
      setGlosses(next)
      syncCardGlosses(cardId, next)
      if (next.length > 0 && glossesRef.current.length === 0) {
        setActiveTab('card_glosses')
        setCollapsed(false)
      }
    }
  }, [cardId, initialGlosses, syncCardGlosses])

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
      syncCardGlosses(cardId, nextGlosses)
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
    [cardId, onGlossesUpdated, syncCardGlosses],
  )

  // Perform lookup for a given term (concordance + AI/lexicon)
  const handleLookup = useCallback(
    async (termToLookup: string, lookupContext?: string | null) => {
      const trimmed = termToLookup.trim()
      if (!trimmed) return

      setSearching(true)
      setLookupError(null)
      setDismissedPromptKey(null)
      setActiveTab('lookup')

      // Check local concordance engine first for instant definition
      await loadConcordanceLexicon()
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
        setLookupError(err instanceof Error ? err.message : 'Lookup failed')
        setActiveEntry(null)
      } finally {
        setSearching(false)
      }
    },
    [cardId, deckName, thematicNature, cardFront, cardBack, refreshRecent],
  )

  // Register with LexiconContext so text selection / Alt+Click in Review route here
  useEffect(() => {
    return registerMarginListener((term, ctx) => {
      onLookupTriggeredRef.current?.()
      setCollapsed(false)
      setQuery(term)
      if (term.trim()) {
        void handleLookup(term, ctx)
      } else if (glossesRef.current.length > 0) {
        setActiveTab('card_glosses')
      } else {
        setActiveTab('lookup')
        void refreshRecent()
      }
    })
  }, [registerMarginListener, handleLookup, refreshRecent])

  // Register populate listener so Ask Local LLM Q&A definitions auto-populate Card Memory
  useEffect(() => {
    return registerPopulateListener((newEntries, serverUpdatedGlosses) => {
      if (!newEntries || newEntries.length === 0) return

      onLookupTriggeredRef.current?.()
      setCollapsed(false)
      if (serverUpdatedGlosses && serverUpdatedGlosses.length > 0) {
        const prevCount = glossesRef.current.length
        setGlosses(serverUpdatedGlosses)
        onGlossesUpdated?.(serverUpdatedGlosses)
        syncCardGlosses(cardId, serverUpdatedGlosses)
        const added = Math.max(0, serverUpdatedGlosses.length - prevCount)
        setSavedNotice(
          added > 0
            ? `⚡ Added ${added} term${added > 1 ? 's' : ''} to Card Memory`
            : '✓ Card Memory updated',
        )
        setTimeout(() => setSavedNotice(null), 3500)
        setActiveTab('card_glosses')
        return
      }

      const current = glossesRef.current
      const existingMap = new Map<string, number>()
      const nextList = [...current]
      nextList.forEach((g, idx) => {
        const k = canonicalTermKey(g.term)
        if (k && !existingMap.has(k)) existingMap.set(k, idx)
      })

      let addedCount = 0
      for (const entry of newEntries) {
        if (!entry?.term) continue
        const k = canonicalTermKey(entry.term)
        if (!k) continue
        if (existingMap.has(k)) {
          const idx = existingMap.get(k)!
          if (!nextList[idx].context_explanation && entry.context_explanation) {
            nextList[idx] = { ...nextList[idx], context_explanation: entry.context_explanation }
          }
        } else {
          existingMap.set(k, nextList.length)
          nextList.push({
            ...entry,
            pinned_at: entry.pinned_at || new Date().toISOString(),
          })
          addedCount++
        }
      }

      if (addedCount > 0 || nextList.length !== current.length) {
        void persistGlosses(
          nextList,
          addedCount > 0
            ? `⚡ Added ${addedCount} term${addedCount > 1 ? 's' : ''} to Card Memory`
            : '✓ Updated Card Memory',
        )
        setActiveTab('card_glosses')
      }
    })
  }, [registerPopulateListener, onGlossesUpdated, persistGlosses])

  const handleAutoExtractTerms = useCallback(async () => {
    if (extractingTerms || (!cardFront && !cardBack)) return
    setExtractingTerms(true)
    setLookupError(null)
    try {
      const res = await api.askDeckQuestion({
        question:
          'Explain the key terms, identifiers, methods, and syntax in this card as concise bullet definitions (* `term`: definition).',
        selected_code: cardBack || cardFront || '',
        full_code: cardBack || cardFront || '',
        language: codeLanguage,
        context: cardFront || deckName || '',
        deck_id: deckId || null,
        card_id: cardId || null,
      })
      if (res.extracted_glosses && res.extracted_glosses.length > 0) {
        populateCardGlosses(res.extracted_glosses, res.updated_card_glosses)
      } else {
        setSavedNotice('No extra terms extracted')
        setTimeout(() => setSavedNotice(null), 3000)
      }
    } catch (err) {
      setLookupError(err instanceof Error ? err.message : 'Failed to extract terms with Local LLM')
    } finally {
      setExtractingTerms(false)
    }
  }, [
    extractingTerms,
    cardFront,
    cardBack,
    codeLanguage,
    deckName,
    deckId,
    cardId,
    populateCardGlosses,
  ])

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
      if (isTermInGlosses(glosses, item.term)) return

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
      const targetLower = termToRemove.toLowerCase().trim()
      const targetCanon = canonicalTermKey(termToRemove)
      const next = glosses.filter((g) => {
        const gt = (g.term || '').toLowerCase().trim()
        return gt !== targetLower && (!targetCanon || canonicalTermKey(gt) !== targetCanon)
      })
      void persistGlosses(next, `Removed "${termToRemove}" from card`)
    },
    [glosses, persistGlosses],
  )

  // Check if current active entry or concordance is already pinned
  const currentLookupTerm = activeEntry?.term || activeConcordance?.term || ''
  const currentLookupKey = canonicalTermKey(currentLookupTerm) || currentLookupTerm.toLowerCase().trim()
  const isCurrentLookupPinned = useMemo(
    () => isTermInGlosses(glosses, currentLookupTerm),
    [glosses, currentLookupTerm],
  )

  const toggleCollapse = () => {
    const next = !collapsed
    setCollapsed(next)
    try {
      localStorage.setItem('memorization.marginLexiconCollapsed', String(next))
    } catch {}
  }

  if (collapsedRailOnDesktop && collapsed) {
    return (
      <>
        {/* Desktop Slim Vertical Rail in Right Margin */}
        <button
          type="button"
          onClick={toggleCollapse}
          className="hidden xl:flex flex-col items-center py-4 px-2 w-12 rounded-2xl border border-sky-500/30 bg-[#0b101b]/95 hover:bg-sky-950/50 hover:border-sky-400/60 shadow-xl text-slate-200 transition-all cursor-pointer select-none group min-h-[220px]"
          title="Expand Card Lexicon & Definitions margin panel"
        >
          <span className="flex h-2 w-2 rounded-full bg-sky-400 mb-3 animate-pulse" />
          <div className="flex-1 flex items-center justify-center">
            <span
              className="text-[11px] font-bold tracking-wider uppercase text-sky-300 group-hover:text-white whitespace-nowrap"
              style={{ writingMode: 'vertical-rl' }}
            >
              Lexicon {glosses.length > 0 ? `(${glosses.length})` : ''}
            </span>
          </div>
          {glosses.length > 0 && (
            <span className="mt-2 rounded-full bg-sky-500/25 border border-sky-400/50 px-1.5 py-0.5 text-[10px] font-bold text-sky-200">
              {glosses.length}
            </span>
          )}
        </button>

        {/* Mobile Horizontal Header */}
        <div className="xl:hidden w-full rounded-2xl border border-sky-500/25 bg-[#0b101b]/95 shadow-xl px-3.5 py-2.5 flex items-center justify-between">
          <span className="text-xs font-bold text-sky-200 uppercase">
            Concordance &amp; Lexicon {glosses.length > 0 ? `(${glosses.length})` : ''}
          </span>
          <button
            type="button"
            onClick={toggleCollapse}
            className="text-xs text-sky-300 hover:text-white px-2 py-0.5 rounded bg-sky-950/60 border border-sky-500/40"
          >
            ▼ Show
          </button>
        </div>
      </>
    )
  }

  return (
    <div
      className={
        embedded
          ? 'w-full h-full flex flex-col min-h-0 rounded-none border-0 bg-[#111318] text-slate-100 font-sans overflow-hidden'
          : 'w-full rounded-2xl border border-sky-500/25 bg-[#0b101b]/95 shadow-xl backdrop-blur-md text-slate-100 font-sans overflow-hidden transition-all duration-200'
      }
    >
      {/* Header Bar */}
      <div
        className={
          embedded
            ? 'h-10 shrink-0 px-3 bg-[#171920] border-b border-[#2a2d34] flex items-center justify-between gap-2'
            : 'px-3.5 py-2.5 bg-gradient-to-r from-sky-950/80 via-slate-900 to-indigo-950/60 border-b border-sky-500/20 flex items-center justify-between gap-2'
        }
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
          <h3 className="text-xs font-bold text-sky-200 tracking-wide uppercase truncate">
            Concordance &amp; Lexicon
          </h3>
          {glosses.length > 0 && (
            <span className="rounded-full bg-sky-500/20 border border-sky-400/40 px-2 py-0.2 text-[10px] font-semibold text-sky-300 shrink-0">
              {glosses.length}
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
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 text-xs transition cursor-pointer"
            title={collapsed ? 'Expand panel' : 'Collapse panel'}
          >
            {collapsed ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className={embedded ? 'p-3 flex flex-col flex-1 min-h-0 gap-2.5' : 'p-3 space-y-3'}>
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
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
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
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
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
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
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

          {/* TAB 1: CARD MEMORY & MARGINALIA */}
          {activeTab === 'card_glosses' && (
            <div
              className={
                embedded
                  ? 'space-y-2.5 flex-1 min-h-0 overflow-y-auto pr-1'
                  : 'space-y-2.5 max-h-[600px] overflow-y-auto pr-1'
              }
            >
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[10px] text-sky-300">
                  Card Glosses ({glosses.length})
                </span>
                <span className="text-[10px] text-slate-500 italic">
                  Persists across reviews
                </span>
              </div>

              {glosses.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700/60 bg-slate-900/30 p-4 text-center space-y-2.5">
                  <p className="text-xs text-slate-300 font-medium">No definitions pinned yet</p>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Ask <strong className="text-emerald-300">Ask LLM</strong> for term definitions, Alt+Click a word, or search above—they will auto-save here for this card.
                  </p>
                  {(cardBack || cardFront) && (
                    <button
                      type="button"
                      disabled={extractingTerms}
                      onClick={() => void handleAutoExtractTerms()}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-950/50 px-3 py-1.5 text-[11px] font-semibold text-emerald-200 hover:bg-emerald-900/60 transition cursor-pointer disabled:opacity-50"
                      title="Ask Local LLM to extract key term definitions for this card automatically"
                    >
                      {extractingTerms ? (
                        <>
                          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                          <span>Extracting Terms…</span>
                        </>
                      ) : (
                        <span>✨ Auto-Extract Key Terms</span>
                      )}
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {glosses.map((item, idx) => {
                    const isCodeTerm =
                      looksLikeCodeTerm(item.term) ||
                      Boolean(item.domain && /typescript|javascript|python|java|code|c\+\+/i.test(item.domain))
                    return (
                      <div
                        key={idx}
                        className="rounded-xl border border-sky-500/20 bg-slate-900/80 p-2.5 space-y-1.5 shadow-sm hover:border-sky-400/40 transition group"
                      >
                        <div className="flex items-baseline justify-between gap-1.5">
                          <div className="flex items-baseline gap-1.5 flex-wrap min-w-0">
                            <h4
                              className={`text-xs font-bold ${
                                isCodeTerm ? 'font-mono text-emerald-300' : 'text-sky-200 capitalize'
                              }`}
                            >
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
                          {renderInlineBackticks(item.definition)}
                        </p>

                        {item.definitions && item.definitions.length > 0 && (
                          <ul className="text-xs text-slate-300 space-y-1 list-disc pl-4 mt-1">
                            {item.definitions.map((d, dIdx) => (
                              <li key={dIdx} className="leading-snug">{renderInlineBackticks(d)}</li>
                            ))}
                          </ul>
                        )}

                        {item.context_explanation && (
                          <p className="text-[11px] text-sky-300/80 bg-sky-950/40 rounded p-1.5 border border-sky-500/15 leading-snug">
                            {renderInlineBackticks(item.context_explanation)}
                          </p>
                        )}

                        {item.example && (
                          <pre className="text-[10px] font-mono text-emerald-300 bg-slate-950/80 p-1.5 rounded overflow-x-auto whitespace-pre-wrap">
                            {item.example}
                          </pre>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: ACTIVE LOOKUP */}
          {activeTab === 'lookup' && (
            <div
              className={
                embedded
                  ? 'space-y-3 flex-1 min-h-0 overflow-y-auto pr-1'
                  : 'space-y-3 max-h-[520px] overflow-y-auto pr-1'
              }
            >
              {lookupError && !searching && (
                <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-200 space-y-1">
                  <p className="font-semibold">AI Lexicon lookup failed</p>
                  <p className="text-[11px] text-rose-300/80">{lookupError}</p>
                </div>
              )}
              {searching ? (
                <div className="py-8 text-center space-y-2">
                  <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
                  <p className="text-xs text-slate-400">Consulting concordance &amp; AI lexicon…</p>
                </div>
              ) : activeEntry || activeConcordance ? (
                <div className="space-y-3">
                  {/* Title & Pin Button */}
                  <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
                    <div className="min-w-0">
                      <h4
                        className={`text-sm font-bold text-sky-200 truncate ${
                          looksLikeCodeTerm(currentLookupTerm) ? 'font-mono' : 'capitalize'
                        }`}
                      >
                        {currentLookupTerm}
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

                  {/* Prompt user to add LLM lookup result to this card's definitions list */}
                  {cardId && (isCurrentLookupPinned || dismissedPromptKey !== currentLookupKey) && (
                    <AddToDefinitionsPrompt
                      term={currentLookupTerm}
                      alreadyAdded={isCurrentLookupPinned}
                      saving={saving}
                      onViewList={() => setActiveTab('card_glosses')}
                      onConfirm={() => {
                        const def = activeEntry?.definition || activeConcordance?.definition || ''
                        handlePinItem({
                          term: currentLookupTerm,
                          definition: def,
                          domain: activeEntry?.domain || activeConcordance?.category || undefined,
                          context_explanation: activeEntry?.context_explanation || undefined,
                          example: activeEntry?.example || activeConcordance?.leetCodeRelevance || undefined,
                          source: activeConcordance ? 'MIT Concordance' : 'AI Lexicon',
                        })
                      }}
                      onDismiss={() => setDismissedPromptKey(currentLookupKey)}
                    />
                  )}

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
            <div
              className={
                embedded
                  ? 'space-y-2 flex-1 min-h-0 overflow-y-auto pr-1'
                  : 'space-y-2 max-h-[520px] overflow-y-auto pr-1'
              }
            >
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
          <div
            className={`pt-2 border-t flex items-center justify-between text-[10px] text-slate-500 shrink-0 ${
              embedded ? 'border-[#262932]' : 'border-slate-800/80'
            }`}
          >
            <span>Alt+Click word to define in margin</span>
            <span>💾 Auto-synced</span>
          </div>
        </div>
      )}
    </div>
  )
}
