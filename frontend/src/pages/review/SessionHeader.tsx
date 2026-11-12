import { useState } from 'react'
import type { Deck, QueueItem, SessionSummary } from '../../api/types'

export function SessionHeader({
  session,
  outcome,
  branchActive,
  onClearBranch,
  deckActive,
  deckName,
  learnMode,
  onToggleLearnMode,
  blitzActive,
  onStartBlitz,
  persistActive,
  persistDeckName,
  persistUnseenOnly,
  onExitPersist,
  persistProgress,
  allCardsRunActive,
  allCardsRunDeckName,
  onExitAllCardsRun,
  allCardsRunProgress,
  onStartAllCardsRun,
  allDecks,
  onStartPersist,
  savedCount,
  onOpenSavedDrawer,
  previousCard,
  onRetryPreviousCard,
}: {
  session: SessionSummary | null
  outcome?: string | null
  branchActive?: boolean
  onClearBranch?: () => void
  deckActive?: boolean
  deckName?: string
  learnMode?: boolean
  onToggleLearnMode?: () => void
  blitzActive?: boolean
  onStartBlitz?: (sec: number) => void
  persistActive?: boolean
  persistDeckName?: string
  persistUnseenOnly?: boolean
  onExitPersist?: () => void
  persistProgress?: { grasped: number; total: number; round: number }
  allCardsRunActive?: boolean
  allCardsRunDeckName?: string
  onExitAllCardsRun?: () => void
  allCardsRunProgress?: { current: number; total: number }
  onStartAllCardsRun?: (deckId: string, deckName?: string) => void
  allDecks?: Deck[]
  onStartPersist?: (deckId: string, deckName?: string, unseenOnly?: boolean) => void
  savedCount?: number
  onOpenSavedDrawer?: () => void
  previousCard?: QueueItem | null
  onRetryPreviousCard?: () => void
}) {
  const [quickPersistUnseenOnly, setQuickPersistUnseenOnly] = useState(false)
  if (!session && !persistActive && !allCardsRunActive) return null
  const counts = session?.counts
  const caps = session?.caps
  const planned = ((counts?.review ?? 0) + (counts?.new ?? 0) + (counts?.ir ?? 0))

  const [modesOpen, setModesOpen] = useState(false)
  const decksWithCards = (allDecks ?? []).filter((d) => d.card_count > 0).length
  const hasModeLaunchers =
    (!persistActive && !allCardsRunActive && decksWithCards > 0 && Boolean(onStartPersist || onStartAllCardsRun)) ||
    Boolean(onStartBlitz && !blitzActive)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {allCardsRunActive && (
          <span className="chip border-purple-500/50 bg-purple-500/15 text-purple-200 font-semibold flex items-center gap-1.5 shadow-sm">
            <span>Run: {allCardsRunDeckName || 'Current Deck'}</span>
            {allCardsRunProgress && (
              <span className="text-[0.625rem] text-purple-300/90 font-mono">
                ({allCardsRunProgress.current}/{allCardsRunProgress.total} · Easiest → Hardest)
              </span>
            )}
            {onExitAllCardsRun && (
              <button
                type="button"
                className="ml-1 text-slate-400 hover:text-white underline text-[0.6875rem] cursor-pointer"
                onClick={onExitAllCardsRun}
                title="Exit All Cards Run and return to FSRS queue"
              >
                exit
              </button>
            )}
          </span>
        )}

        {persistActive && (
          <span className="chip border-amber-500/50 bg-amber-500/15 text-amber-200 font-semibold flex items-center gap-1.5 shadow-sm">
            <span>Persist{persistUnseenOnly ? ' (Unseen)' : ''}: {persistDeckName || 'Current Deck'}</span>
            {persistProgress && (
              <span className="text-[0.625rem] text-amber-300/90 font-mono">
                ({persistProgress.grasped}/{persistProgress.total} Easy · R{persistProgress.round})
              </span>
            )}
            {onExitPersist && (
              <button
                type="button"
                className="ml-1 text-slate-400 hover:text-white underline"
                onClick={onExitPersist}
                title="Exit persist mode"
              >
                exit
              </button>
            )}
          </span>
        )}

        {branchActive && (
          <span className="chip border-sky-500/40 text-sky-300">
            branch-scoped
            {onClearBranch && (
              <button className="ml-2 underline" onClick={onClearBranch}>
                exit
              </button>
            )}
          </span>
        )}

        {deckActive && (
          <span className="chip border-sky-500/50 bg-sky-500/10 text-sky-200 flex items-center gap-1.5 shadow-sm">
            <span>Deck Tree: {deckName || 'Deck + Subdecks'}</span>
            {onClearBranch && (
              <button
                type="button"
                className="ml-1 text-slate-400 hover:text-white underline text-[0.6875rem]"
                onClick={onClearBranch}
                title="Switch to studying all decks in collection"
              >
                study all
              </button>
            )}
          </span>
        )}

        {!branchActive && !deckActive && !persistActive && !allCardsRunActive && (
          <span className="chip border-emerald-500/40 bg-emerald-500/10 text-emerald-200 font-medium">
            Collection: All Decks
          </span>
        )}

        {session && (
          <>
            <span className="chip">{counts?.review ?? 0} reviews</span>
            <span className="chip">{counts?.new ?? 0} new</span>
            <span className="chip">{counts?.ir ?? 0} reading</span>
            <span className="chip">~{Math.round(session.budget_seconds / 60)} min budget</span>
            {caps && caps.reviews_done_today > 0 && (
              <span className="chip">{caps.reviews_done_today} done today</span>
            )}
            {planned === 0 && <span className="chip">queue clear</span>}
          </>
        )}

        {/* Persist, All Cards Run and Blitz are ways to *start* a different kind
            of session, not things you need while answering a card. They sit
            behind one toggle so the row above the card stays a single line. */}
        {hasModeLaunchers && (
          <button
            type="button"
            className={`chip transition cursor-pointer ${
              modesOpen ? 'border-sky-500/50 text-sky-200' : 'hover:text-slate-200'
            }`}
            aria-expanded={modesOpen}
            aria-controls="review-study-modes"
            onClick={() => setModesOpen((open) => !open)}
            title="Persist drill, All Cards Run and Blitz sprint"
          >
            Study modes {modesOpen ? '▴' : '▾'}
          </button>
        )}

        {hasModeLaunchers && modesOpen && (
          <div
            id="review-study-modes"
            className="order-last flex basis-full flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border border-ink-line bg-ink-soft/60 px-3 py-2"
          >
            {/* Quick Persist Deck Selector (when not in persist mode) */}
            {!persistActive && !allCardsRunActive && allDecks && allDecks.filter((d) => d.card_count > 0).length > 0 && onStartPersist && (
              <div className="flex items-center gap-1.5">
                <span className="text-[0.6875rem] text-amber-400 font-medium">Persist Deck:</span>
                <label className="flex items-center gap-1 text-[0.6875rem] text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={quickPersistUnseenOnly}
                    onChange={(e) => setQuickPersistUnseenOnly(e.target.checked)}
                    className="rounded border-slate-700 bg-ink-soft text-amber-500 focus:ring-0 w-3 h-3 cursor-pointer"
                  />
                  <span className="text-[0.625rem] text-amber-300/80">Unseen only</span>
                </label>
                <select
                  aria-label="Deck to drill in persist mode"
                  className="rounded border border-amber-500/30 bg-ink-soft px-2 py-0.5 text-[0.6875rem] text-amber-200 hover:border-amber-400 cursor-pointer"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      const d = allDecks.find((deck) => deck.id === e.target.value)
                      onStartPersist(e.target.value, d?.name, quickPersistUnseenOnly)
                      e.target.value = ''
                    }
                  }}
                >
                  <option value="" disabled>
                    Select deck to drill…
                  </option>
                  {allDecks
                    .filter((d) => d.card_count > 0)
                    .map((d) => {
                      const viewedPct = d.stats && d.stats.total_cards > 0
                        ? Math.round(d.stats.viewed_ratio * 100)
                        : null
                      return (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.card_count} cards{viewedPct !== null ? ` · ${viewedPct}% viewed` : ''}{d.new_count > 0 ? ` · ${d.new_count} unseen` : ''})
                        </option>
                      )
                    })}
                </select>
              </div>
            )}

            {/* Quick All Cards Run Selector */}
            {!allCardsRunActive && !persistActive && allDecks && allDecks.filter((d) => d.card_count > 0).length > 0 && onStartAllCardsRun && (
              <div className="flex items-center gap-1.5">
                <span className="text-[0.6875rem] text-purple-400 font-medium">All Cards Run:</span>
                <select
                  aria-label="Deck for an All Cards Run"
                  className="rounded border border-purple-500/30 bg-ink-soft px-2 py-0.5 text-[0.6875rem] text-purple-200 hover:border-purple-400 cursor-pointer"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      const d = allDecks.find((deck) => deck.id === e.target.value)
                      onStartAllCardsRun(e.target.value, d?.name)
                      e.target.value = ''
                    }
                  }}
                >
                  <option value="" disabled>
                    Select deck to run…
                  </option>
                  {allDecks
                    .filter((d) => d.card_count > 0)
                    .map((d) => {
                      const viewedPct = d.stats && d.stats.total_cards > 0
                        ? Math.round(d.stats.viewed_ratio * 100)
                        : null
                      return (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.card_count} cards{viewedPct !== null ? ` · ${viewedPct}% viewed` : ''})
                        </option>
                      )
                    })}
                </select>
              </div>
            )}

            {/* Blitz Mode Sprint Triggers */}
            {onStartBlitz && !blitzActive && (
              <div className="flex items-center gap-1">
                <span className="text-[0.6875rem] text-amber-400 font-medium">Blitz Sprint:</span>
                <button
                  className="chip hover:border-amber-500/40 hover:text-amber-300"
                  onClick={() => onStartBlitz(30)}
                  title="Start high-speed 30 second sprint"
                >
                  30s
                </button>
                <button
                  className="chip hover:border-amber-500/40 hover:text-amber-300"
                  onClick={() => onStartBlitz(60)}
                  title="Start high-speed 60 second sprint"
                >
                  60s
                </button>
                <button
                  className="chip hover:border-amber-500/40 hover:text-amber-300"
                  onClick={() => onStartBlitz(90)}
                  title="Start high-speed 90 second sprint"
                >
                  90s
                </button>
              </div>
            )}
          </div>
        )}

        {savedCount !== undefined && savedCount > 0 && onOpenSavedDrawer && (
          <button
            type="button"
            onClick={onOpenSavedDrawer}
            className="chip border-indigo-500/50 bg-indigo-500/15 text-indigo-200 hover:bg-indigo-500/25 hover:text-white transition cursor-pointer flex items-center gap-1.5 font-semibold shadow-xs"
            title="Open saved cards shelf (Alt+Shift+S)"
          >
            
            <span>Saved for Later ({savedCount})</span>
          </button>
        )}

        {onToggleLearnMode && (
          <button
            className={`chip ml-auto transition ${
              learnMode ? 'border-sky-500/40 text-sky-300' : 'hover:text-slate-300'
            }`}
            onClick={onToggleLearnMode}
            title="Read a short lesson from the card's source before each question"
          >
            Learn &amp; Practice {learnMode ? 'on' : 'off'}
          </button>
        )}
      </div>

      {outcome && (
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <p className="text-slate-500">Last: {outcome}</p>
          {onRetryPreviousCard && previousCard && (
            <button
              type="button"
              onClick={onRetryPreviousCard}
              className="inline-flex items-center gap-1.5 text-[0.6875rem] text-amber-400 hover:text-amber-300 hover:underline cursor-pointer font-medium transition"
              title={`Retry previous card: "${previousCard.title || previousCard.front?.slice(0, 40)}..."`}
            >
             <span> Retry Previous Card</span>
              <span className="text-slate-500 text-[0.625rem]">
                ({previousCard.title || (previousCard.front ? previousCard.front.slice(0, 25) + '…' : 'card')})
              </span>
            </button>
          )}
        </div>
      )}

      {/* §3.1: guardrails must be visible, or a smoothed backlog looks like a bug.
          One strip for all of them: a separate bordered box per note stacked
          two or three banners between the header and the card. */}
      {session?.notes && session.notes.length > 0 && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 rounded-lg border border-sky-500/25 bg-sky-500/5 px-3 py-1.5 text-xs text-sky-200/90">
          {session.notes.map((note, i) => (
            <li key={i} className="flex items-baseline gap-1.5">
              <span aria-hidden="true" className="text-sky-400/70">
                •
              </span>
              <span>{note}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
