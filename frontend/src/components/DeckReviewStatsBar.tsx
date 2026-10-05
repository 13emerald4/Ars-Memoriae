import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'
import type { DeckStats } from '../api/types'

interface DeckReviewStatsBarProps {
  deckId: string | null
  deckName?: string | null
  /** Optional trigger to force refetch when a card is submitted */
  lastUpdated?: number
  className?: string
  onStartPersist?: (deckId: string) => void
  isPersistActive?: boolean
}

const DIFFICULTY_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; text: string; dot: string }
> = {
  Easy: {
    label: 'Easy',
    color: 'bg-emerald-500',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-300',
    dot: 'bg-emerald-400',
  },
  Medium: {
    label: 'Medium',
    color: 'bg-amber-500',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-300',
    dot: 'bg-amber-400',
  },
  Hard: {
    label: 'Hard',
    color: 'bg-rose-500',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    text: 'text-rose-300',
    dot: 'bg-rose-400',
  },
  Unrated: {
    label: 'Unrated',
    color: 'bg-slate-500',
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/30',
    text: 'text-slate-400',
    dot: 'bg-slate-400',
  },
}

const RATING_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; text: string; dot: string }
> = {
  Again: {
    label: 'Again',
    color: 'bg-rose-500',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    text: 'text-rose-300',
    dot: 'bg-rose-400',
  },
  Hard: {
    label: 'Hard',
    color: 'bg-amber-500',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-300',
    dot: 'bg-amber-400',
  },
  Good: {
    label: 'Good',
    color: 'bg-emerald-500',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-300',
    dot: 'bg-emerald-400',
  },
  Easy: {
    label: 'Easy',
    color: 'bg-sky-500',
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/30',
    text: 'text-sky-300',
    dot: 'bg-sky-400',
  },
  Unrated: {
    label: 'Unreviewed',
    color: 'bg-slate-600',
    bg: 'bg-slate-600/10',
    border: 'border-slate-600/30',
    text: 'text-slate-400',
    dot: 'bg-slate-400',
  },
}

export function DeckReviewStatsBar({
  deckId,
  deckName,
  lastUpdated,
  className = '',
  onStartPersist,
  isPersistActive,
}: DeckReviewStatsBarProps) {
  const [stats, setStats] = useState<DeckStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState<boolean>(() => {
    if (typeof localStorage === 'undefined') return true
    return localStorage.getItem('memorization.deckStatsExpanded') !== '0'
  })

  const loadStats = useCallback(async (id: string) => {
    try {
      setLoading(true)
      const data = await api.deckStats(id)
      setStats(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (deckId) {
      void loadStats(deckId)
    } else {
      setStats(null)
    }
  }, [deckId, lastUpdated, loadStats])

  const toggleExpanded = () => {
    setIsExpanded((prev) => {
      const next = !prev
      localStorage.setItem('memorization.deckStatsExpanded', next ? '1' : '0')
      return next
    })
  }

  if (!deckId || !stats) {
    if (!deckName) return null
    return (
      <div
        className={`rounded-xl border border-ink-line/60 bg-ink-soft/40 px-4 py-2 text-xs text-slate-400 flex items-center justify-between ${className}`}
      >
        <div className="flex items-center gap-2">
          <span>📚</span>
          <span className="font-semibold text-slate-200">Deck: {deckName}</span>
        </div>
        {loading && <span className="text-[11px] text-slate-500 animate-pulse">Loading stats…</span>}
      </div>
    )
  }

  const viewedPct = Math.round(stats.viewed_ratio * 100)
  const unviewedCount = stats.total_cards - stats.viewed_cards

  // Sort difficulties in standard order: Easy, Medium, Hard, Unrated, then others
  const sortedDiffKeys = Object.keys(stats.difficulty_counts).sort((a, b) => {
    const order = ['Easy', 'Medium', 'Hard', 'Unrated']
    const idxA = order.indexOf(a)
    const idxB = order.indexOf(b)
    if (idxA !== -1 && idxB !== -1) return idxA - idxB
    if (idxA !== -1) return -1
    if (idxB !== -1) return 1
    return a.localeCompare(b)
  })

  // Sort user recall ratings in standard review order: Again, Hard, Good, Easy, Unrated
  const sortedRatingKeys = stats.rating_counts
    ? Object.keys(stats.rating_counts).sort((a, b) => {
        const order = ['Again', 'Hard', 'Good', 'Easy', 'Unrated']
        const idxA = order.indexOf(a)
        const idxB = order.indexOf(b)
        if (idxA !== -1 && idxB !== -1) return idxA - idxB
        if (idxA !== -1) return -1
        if (idxB !== -1) return 1
        return a.localeCompare(b)
      })
    : []

  return (
    <div
      className={`rounded-2xl border border-sky-500/25 bg-[#0b101b]/95 p-3.5 shadow-lg backdrop-blur text-xs transition-all duration-200 ${className}`}
    >
      {/* Top Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pb-2 border-b border-ink-line/60">
        <div className="flex items-center gap-2">
          <span className="text-base">📚</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-100 text-xs">
                {stats.name || deckName || 'Current Deck'}
              </span>
              <span className="rounded-full bg-sky-950/80 border border-sky-500/30 px-2 py-0.5 text-[10px] font-mono text-sky-200">
                {stats.total_cards} {stats.total_cards === 1 ? 'card' : 'cards total'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px]">
          {/* Quick Metrics Chips */}
          <span
            className="chip border-emerald-500/40 bg-emerald-950/30 text-emerald-300 font-semibold"
            title="Cards studied at least once in this deck"
          >
            ✓ {stats.viewed_cards} viewed ({viewedPct}%)
          </span>
          {stats.new_cards > 0 && (
            <span
              className="chip border-sky-500/40 bg-sky-950/30 text-sky-300 font-semibold"
              title="Brand new cards never yet studied"
            >
              ★ {stats.new_cards} new
            </span>
          )}
          {stats.due_cards > 0 && (
            <span
              className="chip border-amber-500/40 bg-amber-950/30 text-amber-300 font-semibold"
              title="Cards currently due for review"
            >
              ⏱ {stats.due_cards} due
            </span>
          )}

          {onStartPersist && deckId && !isPersistActive && (
            <button
              type="button"
              onClick={() => onStartPersist(deckId)}
              className="flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-200 hover:bg-amber-500/25 transition shadow-sm"
              title="Persist reviewing this deck until all cards are rated Easy"
            >
              <span>⚡ Persist Deck</span>
            </button>
          )}

          <button
            type="button"
            onClick={toggleExpanded}
            className="rounded px-2 py-0.5 text-[11px] font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            title={isExpanded ? 'Collapse deck stats' : 'Expand deck stats'}
          >
            {isExpanded ? 'Hide Details ▲' : 'Deck Stats ▼'}
          </button>
        </div>
      </div>

      {/* Main Expanded Stats View */}
      {isExpanded && (
        <div className="pt-3 space-y-3 animate-in fade-in duration-150">
          {/* 1. CARDS VIEWED PROGRESS BAR */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <span>🎯</span>
                <span>Cards Viewed out of Total:</span>
                <strong className="text-white font-mono">
                  {stats.viewed_cards} / {stats.total_cards}
                </strong>
              </span>
              <span className="font-mono font-bold text-sky-300">{viewedPct}%</span>
            </div>

            {/* Visual Progress Bar */}
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800/80">
              <div
                className="h-full bg-gradient-to-r from-sky-500 to-emerald-400 transition-all duration-500 ease-out"
                style={{ width: `${Math.min(100, Math.max(0, viewedPct))}%` }}
                title={`${stats.viewed_cards} of ${stats.total_cards} cards viewed (${viewedPct}%)`}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>{stats.viewed_cards} studied</span>
              <span>{unviewedCount > 0 ? `${unviewedCount} unstudied remaining` : 'Deck 100% viewed!'}</span>
            </div>
          </div>

          {/* 2. DIFFICULTY RATINGS DISTRIBUTION BAR */}
          <div className="space-y-1.5 pt-1 border-t border-ink-line/40">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <span>📊</span>
                <span>Card Difficulty Distribution:</span>
              </span>
              <span className="text-[10px] text-slate-500">
                {stats.total_cards} cards categorized
              </span>
            </div>

            {/* Segmented Distribution Bar */}
            <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-800/90 shadow-inner">
              {sortedDiffKeys.map((diffKey) => {
                const count = stats.difficulty_counts[diffKey] || 0
                if (count === 0) return null
                const prop = stats.difficulty_proportions[diffKey] || 0
                const widthPct = Math.round(prop * 1000) / 10
                const cfg = DIFFICULTY_CONFIG[diffKey] || {
                  color: 'bg-indigo-500',
                  label: diffKey,
                }

                return (
                  <div
                    key={diffKey}
                    style={{ width: `${widthPct}%` }}
                    className={`${cfg.color} h-full transition-all duration-300 hover:brightness-110`}
                    title={`${diffKey}: ${count} cards (${widthPct}%)`}
                  />
                )
              })}
            </div>

            {/* Difficulty Legend / Proportion Chips */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {sortedDiffKeys.map((diffKey) => {
                const count = stats.difficulty_counts[diffKey] || 0
                if (count === 0 && stats.total_cards > 0 && diffKey === 'Unrated') return null
                const prop = stats.difficulty_proportions[diffKey] || 0
                const pct = (prop * 100).toFixed(1)
                const cfg = DIFFICULTY_CONFIG[diffKey] || {
                  label: diffKey,
                  bg: 'bg-indigo-500/10',
                  border: 'border-indigo-500/30',
                  text: 'text-indigo-300',
                  dot: 'bg-indigo-400',
                }

                return (
                  <div
                    key={diffKey}
                    className={`flex items-center gap-1.5 rounded-lg border ${cfg.border} ${cfg.bg} px-2 py-0.5 text-[11px] font-medium transition hover:scale-105`}
                    title={`${count} of ${stats.total_cards} cards have ${diffKey} difficulty`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                    <span className="text-slate-300">{cfg.label}:</span>
                    <span className={`font-bold font-mono ${cfg.text}`}>{count}</span>
                    <span className="text-[10px] text-slate-500 font-mono">({pct}%)</span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 3. USER RECALL RATINGS DISTRIBUTION BAR */}
          {stats.rating_counts && Object.keys(stats.rating_counts).length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-ink-line/40">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-300 font-medium flex items-center gap-1.5">
                  <span>🧠</span>
                  <span>My Recall Ratings Distribution:</span>
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {stats.total_reviews ? `${stats.total_reviews} reviews logged` : 'Latest card ratings'}
                </span>
              </div>

              {/* Segmented Recall Bar */}
              <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-800/90 shadow-inner">
                {sortedRatingKeys.map((ratingKey) => {
                  const count = stats.rating_counts?.[ratingKey] || 0
                  if (count === 0) return null
                  const prop = stats.rating_proportions?.[ratingKey] || 0
                  const widthPct = Math.round(prop * 1000) / 10
                  const cfg = RATING_CONFIG[ratingKey] || {
                    color: 'bg-indigo-500',
                    label: ratingKey,
                  }

                  return (
                    <div
                      key={ratingKey}
                      style={{ width: `${widthPct}%` }}
                      className={`${cfg.color} h-full transition-all duration-300 hover:brightness-110`}
                      title={`${ratingKey}: ${count} cards (${widthPct}%)`}
                    />
                  )
                })}
              </div>

              {/* Rating Legend / Proportion Chips */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {sortedRatingKeys.map((ratingKey) => {
                  const count = stats.rating_counts?.[ratingKey] || 0
                  if (count === 0 && ratingKey === 'Unrated') return null
                  const prop = stats.rating_proportions?.[ratingKey] || 0
                  const pct = (prop * 100).toFixed(1)
                  const cfg = RATING_CONFIG[ratingKey] || {
                    label: ratingKey,
                    bg: 'bg-indigo-500/10',
                    border: 'border-indigo-500/30',
                    text: 'text-indigo-300',
                    dot: 'bg-indigo-400',
                  }

                  return (
                    <div
                      key={ratingKey}
                      className={`flex items-center gap-1.5 rounded-lg border ${cfg.border} ${cfg.bg} px-2 py-0.5 text-[11px] font-medium transition hover:scale-105`}
                      title={`${count} of ${stats.total_cards} cards rated ${ratingKey}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                      <span className="text-slate-300">{cfg.label}:</span>
                      <span className={`font-bold font-mono ${cfg.text}`}>{count}</span>
                      <span className="text-[10px] text-slate-500 font-mono">({pct}%)</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
