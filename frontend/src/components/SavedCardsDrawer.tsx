import { useState, useMemo, useEffect } from 'react'
import type { SavedCardDraft } from '../utils/savedCardDrafts'
import { getSavedDrafts, removeDraft, clearAllDrafts } from '../utils/savedCardDrafts'
import { CodeEditor } from './CodeEditor'

export interface SavedCardsDrawerProps {
  isOpen: boolean
  onClose: () => void
  onResumeCard: (draft: SavedCardDraft) => void
  currentCardId?: string | null
}

function formatRelativeTime(timestamp: number): string {
  const diffSec = Math.floor((Date.now() - timestamp) / 1000)
  if (diffSec < 60) return 'Just now'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}h ago`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay}d ago`
}

export function SavedCardsDrawer({
  isOpen,
  onClose,
  onResumeCard,
  currentCardId,
}: SavedCardsDrawerProps) {
  const [draftsMap, setDraftsMap] = useState<Record<string, SavedCardDraft>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'code' | 'flashcard'>('all')
  const [expandedDraftId, setExpandedDraftId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Reload drafts when opened or when drafts change
  useEffect(() => {
    if (!isOpen) return
    const update = () => setDraftsMap(getSavedDrafts())
    update()

    window.addEventListener('savedCardDraftsChanged', update)
    return () => window.removeEventListener('savedCardDraftsChanged', update)
  }, [isOpen])

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const draftsList = useMemo(() => {
    return Object.values(draftsMap).sort((a, b) => b.savedAt - a.savedAt)
  }, [draftsMap])

  const filteredDrafts = useMemo(() => {
    return draftsList.filter((draft) => {
      if (filterType === 'code' && !draft.isCodeCard) return false
      if (filterType === 'flashcard' && draft.isCodeCard) return false

      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      const titleMatch = (draft.title || '').toLowerCase().includes(q)
      const deckMatch = (draft.deckName || '').toLowerCase().includes(q)
      const frontMatch = (draft.frontSnippet || '').toLowerCase().includes(q)
      const answerMatch = (draft.answer || '').toLowerCase().includes(q)
      const testMatch = (draft.testCode || '').toLowerCase().includes(q)

      return titleMatch || deckMatch || frontMatch || answerMatch || testMatch
    })
  }, [draftsList, searchQuery, filterType])

  const handleCopyCode = async (draft: SavedCardDraft) => {
    const textToCopy = draft.testCode
      ? `// Solution:\n${draft.answer}\n\n// Tests:\n${draft.testCode}`
      : draft.answer
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopiedId(draft.cardId)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy draft code:', err)
    }
  }

  const handleDiscard = (cardId: string) => {
    if (window.confirm('Discard this saved draft? Your saved code for this card will be removed.')) {
      removeDraft(cardId)
      setDraftsMap(getSavedDrafts())
    }
  }

  const handleClearAll = () => {
    if (
      window.confirm(
        `Are you sure you want to discard all ${draftsList.length} saved drafts? This cannot be undone.`
      )
    ) {
      clearAllDrafts()
      setDraftsMap({})
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-label="Saved for Later Drawer"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl h-full bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-base shadow-sm">
              💾
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  Saved for Later
                </h2>
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">
                  {draftsList.length} {draftsList.length === 1 ? 'card' : 'cards'}
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Saved in-progress answers and code
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {draftsList.length > 0 && (
              <button
                type="button"
                onClick={handleClearAll}
                className="px-2.5 py-1 text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded transition-colors"
                title="Discard all saved drafts"
              >
                Clear all
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors"
              aria-label="Close saved drawer"
              title="Close (Esc)"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Search & Filters */}
        {draftsList.length > 0 && (
          <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Search…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs px-3 py-1.5 pl-8 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <svg
                className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-400 pointer-events-none"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>

            <div className="flex items-center gap-1">
              {(['all', 'code', 'flashcard'] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setFilterType(type)}
                  className={`text-xs px-2.5 py-1 rounded transition-colors ${
                    filterType === type
                      ? 'bg-indigo-600 text-white font-medium shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {type === 'all' ? 'All' : type === 'code' ? 'Code' : 'Flashcards'}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Content list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {draftsList.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 dark:text-slate-400">
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-500 dark:text-indigo-400 flex items-center justify-center text-2xl mb-3 shadow-inner">
                💾
              </div>
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">
                No saved drafts yet
              </h3>
              <p className="text-xs max-w-sm text-slate-500 dark:text-slate-400 mb-4 leading-relaxed">
                When you're working on a challenging card or writing unit tests, click{' '}
                <span className="font-semibold text-indigo-600 dark:text-indigo-400">Save for Later</span>{' '}
                or press <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-[11px] font-mono border border-slate-300 dark:border-slate-700">Alt + L</kbd>.
              </p>
              <div className="text-xs bg-slate-100 dark:bg-slate-800/80 rounded-lg p-3 text-left max-w-xs space-y-1.5 border border-slate-200 dark:border-slate-700/60">
                <div className="font-medium text-slate-700 dark:text-slate-300">Why Save for Later?</div>
                <div className="text-slate-500 dark:text-slate-400 flex items-start gap-1.5">
                  <span>✓</span>
                  <span>Zero penalty to memory rating / FSRS</span>
                </div>
                <div className="text-slate-500 dark:text-slate-400 flex items-start gap-1.5">
                  <span>✓</span>
                  <span>Preserves both your solution code and tests</span>
                </div>
                <div className="text-slate-500 dark:text-slate-400 flex items-start gap-1.5">
                  <span>✓</span>
                  <span>Advances immediately to the next card in queue</span>
                </div>
              </div>
            </div>
          ) : filteredDrafts.length === 0 ? (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400 text-xs">
              No saved drafts match your current filter or query.
            </div>
          ) : (
            filteredDrafts.map((draft) => {
              const isCurrent = draft.cardId === currentCardId
              const isExpanded = expandedDraftId === draft.cardId
              const hasCode = Boolean(draft.answer && draft.answer.trim())
              const hasTests = Boolean(draft.testCode && draft.testCode.trim())

              return (
                <div
                  key={draft.cardId}
                  className={`rounded-lg border transition-all ${
                    isCurrent
                      ? 'border-indigo-400 dark:border-indigo-600 bg-indigo-50/20 dark:bg-indigo-950/20 ring-1 ring-indigo-300 dark:ring-indigo-700'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 hover:border-slate-300 dark:hover:border-slate-700'
                  } shadow-xs p-3 flex flex-col gap-2`}
                >
                  {/* Card Title & Meta Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap mb-1">
                        {isCurrent && (
                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-600 text-white">
                            Current Card
                          </span>
                        )}
                        {draft.deckName && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 truncate max-w-[150px]">
                            {draft.deckName}
                          </span>
                        )}
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                            draft.isCodeCard
                              ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300'
                              : 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300'
                          }`}
                        >
                          {draft.isCodeCard ? '💻 Code' : '📝 Flashcard'}
                        </span>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500">
                          {formatRelativeTime(draft.savedAt)}
                        </span>
                      </div>

                      <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100 line-clamp-2">
                        {draft.title || 'Untitled Card'}
                      </h4>

                      {draft.frontSnippet && (
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mt-0.5 font-normal">
                          {draft.frontSnippet}
                        </p>
                      )}
                    </div>

                    {/* Quick Resume Button */}
                    <button
                      type="button"
                      onClick={() => onResumeCard(draft)}
                      className="shrink-0 flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors"
                      title="Resume this card now"
                    >
                      <span>▶</span>
                      <span>Resume</span>
                    </button>
                  </div>

                  {/* Draft preview summary */}
                  <div className="bg-slate-50 dark:bg-slate-950/60 rounded border border-slate-200/80 dark:border-slate-800/80 p-2 text-xs">
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-600 dark:text-slate-300">
                          {hasCode ? `${draft.answer.split('\n').length} lines solution` : 'Empty answer'}
                        </span>
                        {hasTests && (
                          <>
                            <span>•</span>
                            <span className="font-mono text-slate-600 dark:text-slate-300">
                              {draft.testCode.split('\n').length} lines tests
                            </span>
                          </>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleCopyCode(draft)}
                          className="hover:text-indigo-600 dark:hover:text-indigo-400 flex items-center gap-1 transition-colors"
                          title="Copy draft code"
                        >
                          {copiedId === draft.cardId ? '✓ Copied' : '📋 Copy'}
                        </button>
                        {(hasCode || hasTests) && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedDraftId(isExpanded ? null : draft.cardId)
                            }
                            className="hover:text-slate-800 dark:hover:text-slate-200 transition-colors font-medium"
                          >
                            {isExpanded ? 'Hide ▲' : 'Inspect ▼'}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Expandable Code Inspection */}
                    {isExpanded && (
                      <div className="mt-2 space-y-2 border-t border-slate-200 dark:border-slate-800 pt-2 animate-in fade-in duration-150">
                        {hasCode && (
                          <div>
                            <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">
                              Solution Draft:
                            </div>
                            <div className="h-44 rounded overflow-hidden border border-slate-200 dark:border-slate-700">
                              <CodeEditor
                                code={draft.answer}
                                onChange={() => {}}
                                language={draft.codeLanguage || 'typescript'}
                                readOnly={true}
                                hideHeader={true}
                                hideFooter={true}
                                height="176px"
                              />
                            </div>
                          </div>
                        )}

                        {hasTests && (
                          <div>
                            <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">
                              Unit Tests Draft:
                            </div>
                            <div className="h-36 rounded overflow-hidden border border-slate-200 dark:border-slate-700">
                              <CodeEditor
                                code={draft.testCode}
                                onChange={() => {}}
                                language={draft.codeLanguage || 'typescript'}
                                readOnly={true}
                                hideHeader={true}
                                hideFooter={true}
                                height="144px"
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Footer actions */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-slate-400">
                      ID: {draft.cardId.slice(0, 8)}…
                    </span>
                    <button
                      type="button"
                      onClick={() => handleDiscard(draft.cardId)}
                      className="text-xs text-rose-500 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 transition-colors"
                      title="Discard this draft"
                    >
                      Discard draft
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <div>
            Tip: Press <kbd className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-[10px] font-mono">Alt + L</kbd> anytime during review to save.
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default SavedCardsDrawer
