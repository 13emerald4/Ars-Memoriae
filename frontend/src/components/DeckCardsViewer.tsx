import { useEffect, useState, useMemo, useCallback } from 'react'
import { api } from '../api/client'
import type { QueueItem } from '../api/types'
import { CodeEditor } from './CodeEditor'
import { RichText } from './ui'
import { isCodeCard, extractCleanCode, detectCodeLanguage } from '../utils/codeUtils'

export interface DeckCardsViewerProps {
  isOpen: boolean
  onClose: () => void
  deckId: string | null
  deckName?: string | null
  currentCardId?: string | null
  onSelectCard?: (card: QueueItem) => void
  codeLanguage?: string
}

export function DeckCardsViewer({
  isOpen,
  onClose,
  deckId,
  deckName,
  currentCardId,
  onSelectCard,
  codeLanguage = 'typescript',
}: DeckCardsViewerProps) {
  const [cards, setCards] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'code' | 'flashcard'>('all')
  const [filterDifficulty, setFilterDifficulty] = useState<'all' | 'easy' | 'medium' | 'hard'>('all')
  const [copiedCode, setCopiedCode] = useState(false)
  const [showTestsSection, setShowTestsSection] = useState(false)

  // Fetch cards when opened
  const loadCards = useCallback(async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.deckPersistItems(id)
      setCards(data)
      if (data.length > 0) {
        // If current card is in list, select it; otherwise select first card
        if (currentCardId && data.some((c) => c.id === currentCardId)) {
          setSelectedCardId(currentCardId)
        } else {
          setSelectedCardId(data[0].id)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [currentCardId])

  useEffect(() => {
    if (isOpen && deckId) {
      void loadCards(deckId)
    }
  }, [isOpen, deckId, loadCards])

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // Filter cards based on search query and filter pills
  const filteredCards = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    return cards.filter((c) => {
      // Filter Type
      if (filterType === 'code' && !isCodeCard(c)) return false
      if (filterType === 'flashcard' && isCodeCard(c)) return false

      // Filter Difficulty
      if (filterDifficulty !== 'all') {
        const diff = (c.difficulty || '').toLowerCase()
        if (diff !== filterDifficulty) return false
      }

      // Search query
      if (q) {
        const titleMatch = (c.title || '').toLowerCase().includes(q)
        const frontMatch = (c.front || '').toLowerCase().includes(q)
        const backMatch = (c.back || '').toLowerCase().includes(q)
        const catMatch = (c.category || '').toLowerCase().includes(q)
        const tcMatch = (c.time_complexity || '').toLowerCase().includes(q)
        return titleMatch || frontMatch || backMatch || catMatch || tcMatch
      }

      return true
    })
  }, [cards, searchQuery, filterType, filterDifficulty])

  const selectedCard = useMemo(() => {
    return cards.find((c) => c.id === selectedCardId) || filteredCards[0] || null
  }, [cards, selectedCardId, filteredCards])

  const handleCopyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code)
      setCopiedCode(true)
      setTimeout(() => setCopiedCode(false), 2000)
    } catch {
      // ignore
    }
  }

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Deck cards browser"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="flex flex-col w-full max-w-7xl h-[92vh] max-h-[920px] rounded-2xl border border-sky-500/30 bg-[#12161f] shadow-2xl overflow-hidden text-slate-200">
        {/* ── Top Header Bar ── */}
        <div className="flex flex-wrap items-center justify-between border-b border-ink-line/80 bg-[#181e2b] px-4 py-3 gap-3">
          <div className="flex items-center gap-3">
            <span className="text-xl">🗂️</span>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-sm sm:text-base">
                  {deckName || selectedCard?.deck_name || 'Cards'}
                </h3>
                <span className="rounded-full bg-sky-950/90 border border-sky-500/40 px-2.5 py-0.5 text-xs font-mono text-sky-200">
                  {cards.length} {cards.length === 1 ? 'card' : 'cards'}
                </span>
                {loading && (
                  <span className="text-xs text-sky-400 animate-pulse">Loading…</span>
                )}
              </div>
              <p className="text-[11px] text-slate-400">
                Browse cards in this deck. <kbd className="px-1 rounded bg-[#252f42] text-[10px] font-mono border border-ink-line">Esc</kbd> to close.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {deckId && (
              <button
                type="button"
                onClick={() => void loadCards(deckId)}
                className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border border-ink-line bg-[#1f2637] hover:bg-[#283248] text-slate-300 transition cursor-pointer"
                title="Refresh"
              >
                <span>↻</span>
                <span className="hidden sm:inline">Refresh</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="flex items-center justify-center w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-rose-500/20 hover:border-rose-500/30 border border-transparent transition cursor-pointer"
              title="Close (Esc)"
            >
              ✕
            </button>
          </div>
        </div>

        {/* ── Search & Filter Controls ── */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-line/60 bg-[#141a26] px-4 py-2.5 text-xs">
          <div className="flex-1 min-w-[200px] max-w-md relative">
            <span className="absolute left-2.5 top-2 text-slate-400 pointer-events-none">🔍</span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search cards..."
              className="w-full rounded-lg border border-ink-line/80 bg-[#1b2233] pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition"
              autoFocus
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1.5 text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Type filter */}
            <div className="inline-flex rounded-lg bg-[#1a2131] p-0.5 border border-ink-line/60">
              <button
                type="button"
                onClick={() => setFilterType('all')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterType === 'all'
                    ? 'bg-sky-600/40 text-sky-100 border border-sky-500/50 shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All ({cards.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterType('code')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterType === 'code'
                    ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                💻 Code ({cards.filter(isCodeCard).length})
              </button>
              <button
                type="button"
                onClick={() => setFilterType('flashcard')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterType === 'flashcard'
                    ? 'bg-emerald-600/40 text-emerald-100 border border-emerald-500/50 shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                📝 Flashcards ({cards.filter((c) => !isCodeCard(c)).length})
              </button>
            </div>

            {/* Difficulty filter */}
            <div className="inline-flex rounded-lg bg-[#1a2131] p-0.5 border border-ink-line/60">
              <button
                type="button"
                onClick={() => setFilterDifficulty('all')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'all'
                    ? 'bg-slate-700/60 text-slate-100 border border-slate-500/50 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setFilterDifficulty('easy')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'easy'
                    ? 'bg-emerald-600/40 text-emerald-100 border border-emerald-500/50 font-semibold'
                    : 'text-emerald-400/80 hover:text-emerald-300'
                }`}
              >
                Easy
              </button>
              <button
                type="button"
                onClick={() => setFilterDifficulty('medium')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'medium'
                    ? 'bg-amber-600/40 text-amber-100 border border-amber-500/50 font-semibold'
                    : 'text-amber-400/80 hover:text-amber-300'
                }`}
              >
                Med
              </button>
              <button
                type="button"
                onClick={() => setFilterDifficulty('hard')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'hard'
                    ? 'bg-rose-600/40 text-rose-100 border border-rose-500/50 font-semibold'
                    : 'text-rose-400/80 hover:text-rose-300'
                }`}
              >
                Hard
              </button>
            </div>
          </div>
        </div>

        {/* ── Main 2-Column Split: List on Left, Preview on Right ── */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 min-h-0 divide-y md:divide-y-0 md:divide-x divide-ink-line/60">
          {/* ── Left Column: Cards List ── */}
          <div className="md:col-span-5 lg:col-span-4 flex flex-col h-full bg-[#10141d] min-h-0">
            <div className="p-2 border-b border-ink-line/50 text-[11px] font-medium text-slate-400 flex items-center justify-between bg-[#151a26]/70">
              <span>{filteredCards.length} of {cards.length} cards</span>
              {searchQuery && (
                <span className="text-sky-400 text-[10px]">Filtered</span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-ink-line/40 p-1.5 space-y-1">
              {error && (
                <div className="p-4 text-xs text-rose-300 bg-rose-950/30 border border-rose-500/30 rounded-lg">
                  Failed to load deck cards: {error}
                </div>
              )}

              {filteredCards.length === 0 && !loading && (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No cards found matching your criteria.
                </div>
              )}

              {filteredCards.map((card, idx) => {
                const isSelected = card.id === selectedCard?.id
                const isCurrent = card.id === currentCardId
                const isCode = isCodeCard(card)
                const cardTitle = card.title || (card.front ? card.front.replace(/^#+\s*/, '').slice(0, 50) : `Card #${idx + 1}`)

                return (
                  <button
                    key={card.id}
                    type="button"
                    onClick={() => setSelectedCardId(card.id)}
                    className={`w-full text-left p-2.5 rounded-xl transition cursor-pointer flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-sky-950/60 border border-sky-500/60 shadow-md ring-1 ring-sky-500/30'
                        : 'hover:bg-[#181f2e] border border-transparent text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="font-mono text-[10px] text-slate-500">#{idx + 1}</span>
                        <span className="font-semibold text-xs text-slate-100 truncate">
                          {cardTitle}
                        </span>
                      </div>
                      {isCurrent && (
                        <span className="shrink-0 px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40 text-[9px]">
                          📍 Active
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                      {isCode ? (
                        <span className="px-1.5 py-0.2 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-medium">
                          💻 Code
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.2 rounded bg-slate-700/30 text-slate-300 border border-slate-600/30 font-medium">
                          📝 Flashcard
                        </span>
                      )}

                      {card.difficulty && (
                        <span
                          className={`px-1.5 py-0.2 rounded border font-medium ${
                            card.difficulty.toLowerCase() === 'easy'
                              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                              : card.difficulty.toLowerCase() === 'hard'
                              ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                              : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                          }`}
                        >
                          {card.difficulty}
                        </span>
                      )}

                      {card.time_complexity && (
                        <span className="px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-300 border border-sky-500/30 font-mono text-[9px]">
                          {card.time_complexity}
                        </span>
                      )}

                      {card.state && (
                        <span className="text-slate-500 capitalize text-[10px]">
                          • {card.state}
                        </span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* ── Right Column: Selected Card Detail Preview ── */}
          <div className="md:col-span-7 lg:col-span-8 flex flex-col h-full bg-[#121620] min-h-0 overflow-y-auto">
            {selectedCard ? (
              <div className="p-4 sm:p-6 space-y-5">
                {/* ── Preview Header & Action Bar ── */}
                <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-ink-line/60">
                  <div className="space-y-1 max-w-xl">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-sky-950/80 border border-sky-500/40 px-2 py-0.5 text-xs font-mono text-sky-200">
                        {isCodeCard(selectedCard) ? '💻 Code' : '📝 Flashcard'}
                      </span>
                      {selectedCard.category && (
                        <span className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-xs text-slate-300">
                          {selectedCard.category}
                        </span>
                      )}
                      {selectedCard.difficulty && (
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-medium border ${
                            selectedCard.difficulty.toLowerCase() === 'easy'
                              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                              : selectedCard.difficulty.toLowerCase() === 'hard'
                              ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                              : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                          }`}
                        >
                          {selectedCard.difficulty}
                        </span>
                      )}
                      {selectedCard.time_complexity && (
                        <span className="rounded bg-sky-500/10 px-2 py-0.5 text-xs font-mono text-sky-300 border border-sky-500/30">
                          ⏱ {selectedCard.time_complexity}
                        </span>
                      )}
                      {selectedCard.space_complexity && (
                        <span className="rounded bg-purple-500/10 px-2 py-0.5 text-xs font-mono text-purple-300 border border-purple-500/30">
                          💾 {selectedCard.space_complexity}
                        </span>
                      )}
                    </div>
                    <h2 className="text-base sm:text-lg font-bold text-white">
                      {selectedCard.title || 'Card Preview'}
                    </h2>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap items-center gap-2">
                    {onSelectCard && (
                      <button
                        type="button"
                        onClick={() => onSelectCard(selectedCard)}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md transition cursor-pointer"
                        title="Study now"
                      >
                        <span>🎯</span>
                        <span>Study Now</span>
                      </button>
                    )}

                    {selectedCard.back && (
                      <button
                        type="button"
                        onClick={() => void handleCopyCode(extractCleanCode(selectedCard.back))}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-line bg-[#1c2333] hover:bg-[#252f44] text-slate-200 text-xs font-medium transition cursor-pointer"
                        title="Copy"
                      >
                        <span>{copiedCode ? '✓ Copied' : '📋 Copy'}</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* ── Prompt / Front Statement ── */}
                <div className="rounded-xl border border-ink-line/80 bg-[#161c28] p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <span>❓</span>
                      <span>Question</span>
                    </span>
                  </div>
                  <div className="text-xs sm:text-sm text-slate-200 leading-relaxed">
                    <RichText text={selectedCard.front || 'No prompt specified'} />
                  </div>

                  {selectedCard.edge_cases && selectedCard.edge_cases.length > 0 && (
                    <div className="pt-2 border-t border-ink-line/50 text-xs flex flex-wrap items-center gap-2">
                      <span className="text-amber-400 font-medium">Edge Cases:</span>
                      {selectedCard.edge_cases.map((ec, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-200 border border-amber-500/30 text-[11px]"
                        >
                          {ec}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* ── Reference Solution ── */}
                <div className="rounded-xl border border-ink-line/80 bg-[#161c28] overflow-hidden space-y-0">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-ink-line/70 bg-[#19202e] text-xs font-semibold text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <span>📖</span>
                      <span>Reference</span>
                    </span>
                    {selectedCard.time_complexity && (
                      <span className="font-mono text-[10px] text-sky-300">
                        Target: {selectedCard.time_complexity}
                      </span>
                    )}
                  </div>

                  {isCodeCard(selectedCard) ? (
                    <CodeEditor
                      code={extractCleanCode(selectedCard.back)}
                      onChange={() => {}}
                      language={detectCodeLanguage(selectedCard.back, codeLanguage)}
                      readOnly={true}
                      height="auto"
                      hideHeader={true}
                      borderless={true}
                      placeholder="// Reference solution"
                    />
                  ) : (
                    <div className="p-4 text-xs sm:text-sm text-slate-200 leading-relaxed">
                      <RichText text={selectedCard.back || 'No answer specified'} />
                    </div>
                  )}
                </div>

                {/* ── Starter Tests & Test Cases (Collapsible) ── */}
                {isCodeCard(selectedCard) && (
                  <div className="rounded-xl border border-ink-line/80 bg-[#161c28] overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setShowTestsSection((prev) => !prev)}
                      className="w-full flex items-center justify-between px-4 py-2.5 bg-[#19202e] text-xs font-semibold text-slate-300 hover:bg-[#20293a] transition cursor-pointer"
                    >
                      <span className="flex items-center gap-1.5">
                        <span>🧪</span>
                        <span>Unit Tests</span>
                        {selectedCard.test_cases && selectedCard.test_cases.length > 0 && (
                          <span className="rounded-full bg-indigo-950/80 px-2 py-0.2 text-[10px] font-mono text-indigo-300 border border-indigo-500/30">
                            {selectedCard.test_cases.length} cases
                          </span>
                        )}
                      </span>
                      <span className="text-slate-400 text-xs">
                        {showTestsSection ? 'Hide ▲' : 'Show ▼'}
                      </span>
                    </button>

                    {showTestsSection && (
                      <div className="p-4 space-y-4 animate-in fade-in duration-150">
                        {/* Test Cases Table */}
                        {selectedCard.test_cases && selectedCard.test_cases.length > 0 && (
                          <div className="space-y-1.5">
                            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              Test Cases
                            </h4>
                            <div className="overflow-x-auto rounded-lg border border-ink-line/60">
                              <table className="w-full text-left text-xs">
                                <thead className="bg-[#1f2637] text-slate-400 font-mono text-[11px] border-b border-ink-line/60">
                                  <tr>
                                    <th className="px-3 py-1.5">#</th>
                                    <th className="px-3 py-1.5">Input</th>
                                    <th className="px-3 py-1.5">Expected</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-ink-line/40 font-mono text-[11px] bg-[#141924]">
                                  {selectedCard.test_cases.map((tc, idx) => (
                                    <tr key={idx} className="hover:bg-[#1a2130]">
                                      <td className="px-3 py-1.5 text-slate-500 font-bold">{idx + 1}</td>
                                      <td className="px-3 py-1.5 text-sky-200">
                                        {typeof tc.input === 'object'
                                          ? JSON.stringify(tc.input)
                                          : String(tc.input)}
                                      </td>
                                      <td className="px-3 py-1.5 text-emerald-300 font-semibold">
                                        {JSON.stringify(tc.expected)}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}

                        {/* Starter Code */}
                        {selectedCard.starter_code && (
                          <div className="space-y-1.5">
                            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              Starter Code
                            </h4>
                            <CodeEditor
                              code={selectedCard.starter_code}
                              onChange={() => {}}
                              language={codeLanguage}
                              readOnly={true}
                              height="140px"
                              hideHeader={true}
                              borderless={true}
                            />
                          </div>
                        )}

                        {/* Starter Tests */}
                        {selectedCard.starter_tests && (
                          <div className="space-y-1.5">
                            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              Starter Tests
                            </h4>
                            <CodeEditor
                              code={selectedCard.starter_tests}
                              onChange={() => {}}
                              language={codeLanguage}
                              readOnly={true}
                              height="160px"
                              hideHeader={true}
                              borderless={true}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full p-8 text-center text-slate-500 space-y-2">
                <span className="text-3xl">🗂️</span>
                <p className="text-sm">Select a card to preview.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
export default DeckCardsViewer
