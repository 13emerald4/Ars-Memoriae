import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { CardAnalytics } from '../api/types'
import { RichText, Spinner, ErrorNote } from './ui'

export interface CardAnalyticsModalProps {
  cardId: string | null
  isOpen: boolean
  onClose: () => void
  onCardUpdated?: () => void
}

export function CardAnalyticsModal({
  cardId,
  isOpen,
  onClose,
  onCardUpdated,
}: CardAnalyticsModalProps) {
  const navigate = useNavigate()
  const [data, setData] = useState<CardAnalytics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Memory note / anchor editing
  const [memoryNote, setMemoryNote] = useState('')
  const [isSavingNote, setIsSavingNote] = useState(false)
  const [noteSuccess, setNoteSuccess] = useState<string | null>(null)

  // Card content preview toggle
  const [showFullCard, setShowFullCard] = useState(false)

  // Action status (suspend, postpone)
  const [actionBusy, setActionBusy] = useState(false)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const loadAnalytics = useCallback(async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      const res = await api.cardAnalytics(id)
      setData(res)
      setMemoryNote(res.card.documentation || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen && cardId) {
      void loadAnalytics(cardId)
    } else {
      setData(null)
      setError(null)
      setNoteSuccess(null)
      setActionMsg(null)
    }
  }, [isOpen, cardId, loadAnalytics])

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

  // Prevent background scrolling while modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  async function handleSaveMemoryNote() {
    if (!data) return
    setIsSavingNote(true)
    setNoteSuccess(null)
    try {
      const updatedCard = await api.updateCardMemoryNote(data.card.id, memoryNote)
      setData((prev) => (prev ? { ...prev, card: updatedCard } : null))
      setNoteSuccess('Memory anchor note saved successfully!')
      onCardUpdated?.()
      setTimeout(() => setNoteSuccess(null), 3500)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsSavingNote(false)
    }
  }

  async function handleToggleSuspend() {
    if (!data) return
    setActionBusy(true)
    setActionMsg(null)
    try {
      const updated = await api.suspendCard(data.card.id, !data.card.suspended)
      setData((prev) => (prev ? { ...prev, card: updated } : null))
      setActionMsg(updated.suspended ? 'Card suspended.' : 'Card unsuspended.')
      onCardUpdated?.()
      setTimeout(() => setActionMsg(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setActionBusy(false)
    }
  }

  async function handlePostpone() {
    if (!data) return
    setActionBusy(true)
    setActionMsg(null)
    try {
      await api.postponeCard(data.card.id, 4)
      await loadAnalytics(data.card.id)
      setActionMsg('Card postponed by 4 hours.')
      onCardUpdated?.()
      setTimeout(() => setActionMsg(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setActionBusy(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-3 sm:p-6 overflow-y-auto">
      <div className="relative flex flex-col w-full max-w-4xl max-h-[92vh] rounded-2xl border border-ink-line bg-[#0e131f] shadow-2xl overflow-hidden text-slate-100">
        {/* ── Top Header ── */}
        <div className="flex flex-wrap items-center justify-between border-b border-ink-line/80 bg-[#141a27] px-5 py-4 gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-sky-500/15 border border-sky-500/30 px-2.5 py-0.5 text-xs font-semibold text-sky-300">
                {data?.card.deck_name || 'Deck Card'}
              </span>
              {data?.card && (
                <>
                  <span className="chip text-[11px] uppercase tracking-wider font-mono">
                    {data.card.state}
                  </span>
                  {data.card.leech_flag && (
                    <span className="chip border-rose-500/40 bg-rose-500/20 text-rose-300 text-[11px] font-bold">
                      ⚠ Leech
                    </span>
                  )}
                  {data.card.suspended && (
                    <span className="chip border-amber-500/40 bg-amber-500/20 text-amber-300 text-[11px]">
                      Suspended
                    </span>
                  )}
                </>
              )}
            </div>
            <h2 className="mt-1.5 font-bold text-white text-base sm:text-lg truncate">
              {data?.card ? data.card.front.slice(0, 100) : 'Card Analytics & Memory Dynamics'}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            {cardId && (
              <button
                type="button"
                onClick={() => void loadAnalytics(cardId)}
                disabled={loading}
                className="btn px-2.5 py-1 text-xs text-slate-300 flex items-center gap-1.5"
                title="Refresh stats"
              >
                <span>↻</span>
                <span className="hidden sm:inline">Refresh</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-400 hover:text-white hover:bg-rose-500/20 border border-transparent transition text-xl leading-none"
              title="Close (Esc)"
            >
              &times;
            </button>
          </div>
        </div>

        {/* ── Main Modal Scrollable Body ── */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
          {loading && !data && (
            <div className="py-16 flex justify-center">
              <Spinner label="Loading card analytics & memory dynamics…" />
            </div>
          )}

          {error && <ErrorNote error={error} />}

          {actionMsg && (
            <div className="rounded-lg border border-sky-500/40 bg-sky-500/10 px-4 py-2.5 text-xs text-sky-200">
              {actionMsg}
            </div>
          )}

          {data && (
            <>
              {/* ── Card Content Accordion ── */}
              <div className="rounded-xl border border-ink-line bg-[#131927] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Card Content Preview
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowFullCard((prev) => !prev)}
                    className="text-xs text-sky-400 hover:text-sky-300 transition"
                  >
                    {showFullCard ? 'Collapse Preview ▲' : 'Expand Full Card ▼'}
                  </button>
                </div>

                <div className="space-y-2">
                  <div className="text-sm text-slate-200 font-medium">
                    <span className="text-xs font-bold text-sky-400 mr-2">Q:</span>
                    <RichText text={showFullCard ? data.card.front : data.card.front.slice(0, 220) + (data.card.front.length > 220 ? '…' : '')} />
                  </div>
                  {showFullCard && (
                    <div className="pt-2 border-t border-ink-line/60 text-sm text-slate-300">
                      <span className="text-xs font-bold text-emerald-400 mr-2">A:</span>
                      <RichText text={data.card.back} />
                    </div>
                  )}
                </div>

                {data.card.tags && data.card.tags.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    {data.card.tags.map((tag) => (
                      <span key={tag} className="chip text-[10px]">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* ── ⭐ PRIMARY FOCUS: WEAK POINTS & MEMORY COMPONENT ── */}
              <div className="rounded-xl border border-amber-500/40 bg-gradient-to-br from-amber-500/10 via-[#131927] to-[#121825] p-5 space-y-4 shadow-lg">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-500/20 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-6 h-6 rounded-md bg-amber-500/20 text-amber-300 text-sm font-bold">
                      ⚡
                    </span>
                    <div>
                      <h3 className="text-sm font-bold text-amber-200">
                        Memory Component &amp; Weak Points Focus
                      </h3>
                      <p className="text-[11px] text-amber-300/80">
                        Targeted diagnosis of misunderstandings, memory interference, and personal recall anchors.
                      </p>
                    </div>
                  </div>
                  <span className="chip border-amber-500/40 bg-amber-500/20 text-amber-200 text-xs">
                    Targeted Review Aid
                  </span>
                </div>

                {/* 1. Active Stumbling Blocks */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Active Stumbling Blocks Identified by AI
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {data.active_weaknesses.length}{' '}
                      {data.active_weaknesses.length === 1 ? 'active flaw' : 'active flaws'}
                    </span>
                  </div>

                  {data.active_weaknesses.length > 0 ? (
                    <div className="space-y-2">
                      {data.active_weaknesses.map((weakness, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2.5 rounded-lg border border-amber-500/40 bg-amber-500/15 p-3 text-xs text-amber-100"
                        >
                          <span className="text-amber-400 font-bold mt-0.5">⚠</span>
                          <div className="flex-1">
                            <span className="font-semibold text-amber-200">Stumbling Block: </span>
                            <span>{weakness}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-200">
                      <span className="text-emerald-400 font-bold">✓</span>
                      <span>
                        <strong>No Active Stumbling Blocks:</strong> You have consistently demonstrated correct conceptual understanding on this card.
                      </span>
                    </div>
                  )}
                </div>

                {/* 2. Personal Memory Anchor / Mnemonic Notes */}
                <div className="space-y-2 pt-2 border-t border-ink-line/60">
                  <div className="flex items-center justify-between">
                    <div>
                      <label htmlFor="memory-anchor" className="text-xs font-bold uppercase tracking-wider text-slate-300">
                        Personal Memory Anchor &amp; Mnemonic
                      </label>
                      <p className="text-[11px] text-slate-400">
                        Write an intuitive mnemonic, mental hook, or core principle to recalibrate your recall when you stumble.
                      </p>
                    </div>
                    {noteSuccess && (
                      <span className="text-xs font-semibold text-emerald-400 animate-pulse">
                        ✓ {noteSuccess}
                      </span>
                    )}
                  </div>

                  <textarea
                    id="memory-anchor"
                    className="input min-h-[5rem] text-xs font-mono leading-relaxed bg-[#0b0f19] border-slate-700 focus:border-amber-400"
                    placeholder="e.g. Anchor Mnemonic: Singleton = 1 static instance + private constructor. Avoid new() calls!"
                    value={memoryNote}
                    onChange={(e) => setMemoryNote(e.target.value)}
                  />

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[11px] text-slate-500">
                      Stored in card documentation and surfaced during reviews.
                    </span>
                    <button
                      type="button"
                      onClick={handleSaveMemoryNote}
                      disabled={isSavingNote}
                      className="btn btn-primary px-3 py-1 text-xs"
                    >
                      {isSavingNote ? 'Saving…' : 'Save Memory Anchor'}
                    </button>
                  </div>
                </div>

                {/* 3. Longitudinal Weakness History Trajectory */}
                {data.weakness_history && data.weakness_history.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-ink-line/60">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Longitudinal Weakness Trajectory
                    </span>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                      {data.weakness_history.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between rounded bg-[#0b0f19]/80 border border-ink-line px-3 py-1.5 text-xs text-slate-300"
                        >
                          <span className="font-mono text-[11px] text-slate-400">
                            {item.timestamp ? new Date(item.timestamp).toLocaleDateString() : `Step #${idx + 1}`}
                          </span>
                          <span className="truncate max-w-md text-amber-200">
                            {typeof item === 'string' ? item : item.weakness || JSON.stringify(item)}
                          </span>
                          <span className="chip text-[10px] text-slate-400">
                            {item.status || 'Resolved'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* ── FSRS MEMORY DYNAMICS & SCHEDULED PROJECTIONS ── */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    FSRS Memory Dynamics &amp; Interval Projections
                  </h3>
                  <span className="text-[11px] text-slate-500">
                    Calculated via py-fsrs Spaced Repetition Engine
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {/* Retrievability Card */}
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 flex flex-col justify-between space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-400">Retrievability R(t)</span>
                      <span className="text-slate-500 text-xs">Recall Prob.</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span
                        className={`text-2xl font-black ${
                          data.retrievability == null
                            ? 'text-slate-500'
                            : data.retrievability >= 0.9
                            ? 'text-emerald-400'
                            : data.retrievability >= 0.7
                            ? 'text-amber-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {data.retrievability != null
                          ? `${(data.retrievability * 100).toFixed(1)}%`
                          : 'New'}
                      </span>
                      {data.retrievability != null && (
                        <span className="text-[11px] text-slate-400">
                          {data.retrievability >= 0.9 ? 'Optimal' : data.retrievability >= 0.7 ? 'Decaying' : 'Overdue'}
                        </span>
                      )}
                    </div>
                    {/* Visual Meter */}
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          data.retrievability == null
                            ? 'w-0'
                            : data.retrievability >= 0.9
                            ? 'bg-emerald-500'
                            : data.retrievability >= 0.7
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(0, (data.retrievability ?? 0) * 100))}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-slate-500 leading-snug">
                      Probability of successful recall at this moment in time.
                    </p>
                  </div>

                  {/* Stability Card */}
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 flex flex-col justify-between space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-400">Stability (S)</span>
                      <span className="text-slate-500 text-xs">Half-Life</span>
                    </div>
                    <div className="text-2xl font-black text-sky-400">
                      {data.card.stability != null ? `${data.card.stability.toFixed(1)}d` : '0.0d'}
                    </div>
                    <p className="text-[10px] text-slate-500 leading-snug">
                      Expected days until recall probability drops down to 90%.
                    </p>
                  </div>

                  {/* Difficulty Card */}
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 flex flex-col justify-between space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-400">Difficulty (D)</span>
                      <span className="text-slate-500 text-xs">1.0 – 10.0</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-amber-300">
                        {data.card.difficulty != null ? data.card.difficulty.toFixed(1) : '--'}
                      </span>
                      <span className="text-[11px] text-slate-400">/ 10</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500"
                        style={{ width: `${Math.min(100, ((data.card.difficulty ?? 0) / 10) * 100)}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-slate-500 leading-snug">
                      Inherent cognitive complexity calibrated by review grades.
                    </p>
                  </div>

                  {/* Lapses & Priority */}
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 flex flex-col justify-between space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-400">Lapses &amp; Due</span>
                      <span className="text-slate-500 text-xs">Status</span>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-slate-200">
                        {data.card.lapse_count} {data.card.lapse_count === 1 ? 'lapse' : 'lapses'}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {data.card.due ? `Due ${new Date(data.card.due).toLocaleDateString()}` : 'Due now'}
                      </div>
                    </div>
                    <p className="text-[10px] text-slate-500 leading-snug">
                      Priority: {data.card.priority}/100
                    </p>
                  </div>
                </div>

                {/* Simulated Next Intervals */}
                {data.next_intervals && (
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-300">
                        Simulated Next Intervals (If Reviewed Now)
                      </span>
                      <span className="text-[11px] text-slate-500">
                        Determines next due date
                      </span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                      <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-2.5 text-center">
                        <span className="block text-[11px] font-bold uppercase tracking-wider text-rose-300">
                          Again
                        </span>
                        <span className="text-base font-bold text-rose-200 font-mono">
                          {data.next_intervals.again}
                        </span>
                      </div>
                      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-center">
                        <span className="block text-[11px] font-bold uppercase tracking-wider text-amber-300">
                          Hard
                        </span>
                        <span className="text-base font-bold text-amber-200 font-mono">
                          {data.next_intervals.hard}
                        </span>
                      </div>
                      <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 p-2.5 text-center">
                        <span className="block text-[11px] font-bold uppercase tracking-wider text-sky-300">
                          Good
                        </span>
                        <span className="text-base font-bold text-sky-200 font-mono">
                          {data.next_intervals.good}
                        </span>
                      </div>
                      <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-center">
                        <span className="block text-[11px] font-bold uppercase tracking-wider text-emerald-300">
                          Easy
                        </span>
                        <span className="text-base font-bold text-emerald-200 font-mono">
                          {data.next_intervals.easy}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* ── PERFORMANCE, RATINGS & AUTOMATICITY ── */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Performance &amp; Speed Metrics
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {/* Recall Rate */}
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 flex flex-col justify-between space-y-2">
                    <span className="text-xs font-medium text-slate-400">Recall Accuracy</span>
                    <div className="flex items-baseline gap-2">
                      <span
                        className={`text-3xl font-black ${
                          data.total_reviews === 0
                            ? 'text-slate-500'
                            : data.recall_rate >= 80
                            ? 'text-emerald-400'
                            : data.recall_rate >= 60
                            ? 'text-amber-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {data.total_reviews > 0 ? `${data.recall_rate.toFixed(1)}%` : '--'}
                      </span>
                      <span className="text-xs text-slate-400">
                        ({data.total_reviews} {data.total_reviews === 1 ? 'review' : 'reviews'})
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      {data.total_overridden > 0
                        ? `${data.total_overridden} review(s) manually overridden`
                        : 'Graded via AI and FSRS rubrics'}
                    </p>
                  </div>

                  {/* Rating Breakdown Bar */}
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 flex flex-col justify-between space-y-2">
                    <span className="text-xs font-medium text-slate-400">Rating Breakdown</span>
                    {data.total_reviews > 0 ? (
                      <div className="space-y-2">
                        <div className="h-3 w-full rounded-full bg-slate-800 flex overflow-hidden">
                          {data.rating_percentages.again > 0 && (
                            <div
                              className="bg-rose-500"
                              style={{ width: `${data.rating_percentages.again}%` }}
                              title={`Again: ${data.rating_counts.again} (${data.rating_percentages.again}%)`}
                            />
                          )}
                          {data.rating_percentages.hard > 0 && (
                            <div
                              className="bg-amber-500"
                              style={{ width: `${data.rating_percentages.hard}%` }}
                              title={`Hard: ${data.rating_counts.hard} (${data.rating_percentages.hard}%)`}
                            />
                          )}
                          {data.rating_percentages.good > 0 && (
                            <div
                              className="bg-sky-500"
                              style={{ width: `${data.rating_percentages.good}%` }}
                              title={`Good: ${data.rating_counts.good} (${data.rating_percentages.good}%)`}
                            />
                          )}
                          {data.rating_percentages.easy > 0 && (
                            <div
                              className="bg-emerald-500"
                              style={{ width: `${data.rating_percentages.easy}%` }}
                              title={`Easy: ${data.rating_counts.easy} (${data.rating_percentages.easy}%)`}
                            />
                          )}
                        </div>
                        <div className="grid grid-cols-4 gap-1 text-[10px] text-center">
                          <span className="text-rose-400">Again: {data.rating_counts.again || 0}</span>
                          <span className="text-amber-400">Hard: {data.rating_counts.hard || 0}</span>
                          <span className="text-sky-400">Good: {data.rating_counts.good || 0}</span>
                          <span className="text-emerald-400">Easy: {data.rating_counts.easy || 0}</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No rating data yet.</p>
                    )}
                  </div>

                  {/* Response Speed & Automaticity */}
                  <div className="rounded-xl border border-ink-line bg-[#131927] p-4 flex flex-col justify-between space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-400">Latency &amp; Speed</span>
                      {data.automaticity_achieved ? (
                        <span className="chip border-emerald-500/40 bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                          ★ Automaticity
                        </span>
                      ) : (
                        <span className="chip text-[10px] text-slate-400">
                          Deliberative
                        </span>
                      )}
                    </div>
                    <div className="text-2xl font-black text-slate-100 font-mono">
                      {data.avg_latency_ms != null ? `${(data.avg_latency_ms / 1000).toFixed(1)}s` : '--'}
                      <span className="text-xs font-normal text-slate-400 ml-1">avg</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span>Fastest: {data.fastest_latency_ms ? `${(data.fastest_latency_ms / 1000).toFixed(1)}s` : '--'}</span>
                      <span>Slowest: {data.slowest_latency_ms ? `${(data.slowest_latency_ms / 1000).toFixed(1)}s` : '--'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── CHRONOLOGICAL ATTEMPT & REVIEW HISTORY TABLE ── */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Review History &amp; Attempt Transcripts ({data.review_logs.length})
                  </h3>
                  <span className="text-[11px] text-slate-500">
                    Chronological study logs
                  </span>
                </div>

                {data.review_logs.length > 0 ? (
                  <div className="rounded-xl border border-ink-line bg-[#131927] overflow-hidden">
                    <div className="divide-y divide-ink-line/60 max-h-72 overflow-y-auto">
                      {data.review_logs.map((log) => {
                        const gradeColor =
                          log.final_grade === 'easy'
                            ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300'
                            : log.final_grade === 'good'
                            ? 'border-sky-500/40 bg-sky-500/15 text-sky-300'
                            : log.final_grade === 'hard'
                            ? 'border-amber-500/40 bg-amber-500/15 text-amber-300'
                            : 'border-rose-500/40 bg-rose-500/15 text-rose-300'

                        return (
                          <div key={log.id} className="p-3.5 space-y-2 hover:bg-[#182032] transition">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className={`chip font-bold text-xs uppercase ${gradeColor}`}>
                                  {log.final_grade}
                                </span>
                                {log.overridden && (
                                  <span className="chip text-[10px] text-amber-300 border-amber-500/30">
                                    Overridden
                                  </span>
                                )}
                                {log.is_blitz && (
                                  <span className="chip text-[10px] text-sky-300 border-sky-500/30">
                                    ⚡ Blitz
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                                {log.latency_ms && (
                                  <span>{(log.latency_ms / 1000).toFixed(1)}s latency</span>
                                )}
                                <span>{new Date(log.reviewed_at).toLocaleString()}</span>
                              </div>
                            </div>

                            {/* Typed Answer */}
                            {log.typed_answer && (
                              <div className="rounded bg-[#0b0f19] border border-ink-line/80 p-2 text-xs font-mono text-slate-200">
                                <span className="text-slate-500 select-none mr-2">Your Answer:</span>
                                <span>{log.typed_answer}</span>
                              </div>
                            )}

                            {/* AI Critique & Weaknesses */}
                            {log.llm_reasoning && (
                              <p className="text-xs text-slate-400 leading-relaxed">
                                <strong className="text-slate-300">AI Feedback: </strong>
                                {log.llm_reasoning}
                              </p>
                            )}

                            {/* Weaknesses / Improvements Chips */}
                            {log.weaknesses && log.weaknesses.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                                <span className="text-[10px] font-semibold text-rose-300">Flagged Flaws:</span>
                                {log.weaknesses.map((w, idx) => (
                                  <span key={idx} className="chip text-[10px] border-rose-500/30 bg-rose-500/10 text-rose-200">
                                    {w}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-ink-line p-8 text-center text-xs text-slate-500">
                    No review logs recorded for this card yet. Complete your first review session to see attempt analytics.
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* ── Footer Action Bar ── */}
        <div className="flex flex-wrap items-center justify-between border-t border-ink-line/80 bg-[#141a27] px-5 py-3.5 gap-3">
          <div className="flex items-center gap-2">
            {data?.card && (
              <>
                <button
                  type="button"
                  onClick={handleToggleSuspend}
                  disabled={actionBusy}
                  className="btn px-3 py-1.5 text-xs text-slate-300 hover:text-white"
                >
                  {data.card.suspended ? 'Unsuspend Card' : 'Suspend Card'}
                </button>
                <button
                  type="button"
                  onClick={handlePostpone}
                  disabled={actionBusy}
                  className="btn px-3 py-1.5 text-xs text-slate-300 hover:text-white"
                >
                  Postpone 4h
                </button>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                onClose()
                navigate('/review')
              }}
              className="btn btn-primary px-4 py-1.5 text-xs font-semibold"
            >
              Practice in Review
            </button>
            <button
              type="button"
              onClick={onClose}
              className="btn px-4 py-1.5 text-xs"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
