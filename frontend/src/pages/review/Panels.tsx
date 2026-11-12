import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import type { QueueItem, SocraticTurn, StuckAlert } from '../../api/types'
import { formatClock } from '../../components/SessionTimer'
import { RichText } from '../../components/RichText'

/** Stuck-state detector (§ Stuck-state detector): the backend flags an
 *  accuracy slump or a latency spike on `confirm`; this is the nudge — take
 *  it as a prompt to break or work, never a silent behavior change, matching
 *  how every other automatic suggestion in this app stays a proposal. */
export function StuckBanner({
  alert,
  onBreak,
  onDismiss,
}: {
  alert: StuckAlert
  onBreak: () => void
  onDismiss: () => void
}) {
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <p>{alert.message}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button className="btn px-2.5 py-1 text-xs" onClick={onBreak}>
          Take a {alert.suggested_break_minutes}-minute break
        </button>
        <button className="btn px-2.5 py-1 text-xs" onClick={onDismiss}>
          Keep going
        </button>
      </div>
    </div>
  )
}

/** Stands in for the next card until the break ends — the study clock and
 *  bank keep running underneath (SessionTimer is unaffected), only the next
 *  question is held back. */
export function BreakOverlay({ until, onDone }: { until: number; onDone: () => void }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    if (now >= until) onDone()
  }, [now, until, onDone])

  return (
    <div className="card space-y-3 text-center">
      <p className="text-lg text-slate-100">Taking a break</p>
      <p className="font-mono text-3xl tabular-nums text-slate-100">
        {formatClock(Math.max(0, until - now))}
      </p>
      <button className="btn" onClick={onDone}>
        Skip break, keep going
      </button>
    </div>
  )
}

/** Socratic AI Guide: one diagnostic question at a time, never the answer.
 *  Stateless on the server — the whole transcript rides along with each
 *  turn, so there's nothing here to persist across a card change either. */
export function SocraticGuide({
  history,
  input,
  onInputChange,
  loading,
  degraded,
  onTrack,
  onSend,
  onClose,
  onCommit,
  onRetry,
}: {
  history: SocraticTurn[]
  input: string
  onInputChange: (v: string) => void
  loading: boolean
  degraded: string | null
  onTrack: boolean
  onSend: () => void
  onClose: () => void
  onCommit: () => void
  onRetry?: () => void
}) {
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-ink-line bg-ink p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">Guide</span>
        <button className="text-xs text-slate-600 underline hover:text-slate-400" onClick={onClose}>
          close
        </button>
      </div>

      {degraded ? (
        <div className="space-y-2">
          <p className="text-xs text-amber-300 leading-relaxed">
            Guide unavailable ({degraded}).
          </p>
          {onRetry && (
            <div className="pt-1">
              <button
                type="button"
                className="btn text-xs px-2.5 py-1 border-sky-500/40 text-sky-300 hover:bg-sky-500/10"
                onClick={onRetry}
                disabled={loading}
              >
                {loading ? 'Retrying…' : '↻ Retry Guide'}
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          {history.length === 0 && loading && <p className="text-xs text-slate-600">Thinking…</p>}
          <div className="space-y-2">
            {history.map((turn, i) => (
              <p
                key={i}
                className={`text-xs leading-relaxed ${
                  turn.role === 'guide' ? 'text-sky-300' : 'text-slate-300'
                }`}
              >
                <span className="font-medium">{turn.role === 'guide' ? 'Guide: ' : 'You: '}</span>
                {turn.text}
              </p>
            ))}
            {history.length > 0 && loading && <p className="text-xs text-slate-600">Thinking…</p>}
          </div>
          {onTrack && !loading && (
            <div className="flex flex-wrap items-center gap-2 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-1.5">
              <span className="text-xs text-emerald-300">You've got it — write it down.</span>
              <button className="btn px-2 py-0.5 text-xs" onClick={onCommit}>
                Back to my answer
              </button>
            </div>
          )}
          <div className="flex gap-2 pt-1">
            <input
              className="input flex-1 py-1 text-xs"
              placeholder="Reply to the guide…"
              value={input}
              disabled={loading}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey && input.trim()) {
                  e.preventDefault()
                  onSend()
                }
              }}
            />
            <button
              className="btn px-2.5 py-1 text-xs"
              disabled={loading || !input.trim()}
              onClick={onSend}
            >
              Send
            </button>
          </div>
        </>
      )}
    </div>
  )
}

/** IR extracts surfaced inside the review session (§9.4). */
export function ExtractCard({ item, onDone }: { item: QueueItem; onDone: () => void }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  async function postpone(days: number) {
    setBusy(true)
    try {
      await api.scheduleExtract(item.id, { days })
      onDone()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="chip">reading</span>
        <span className="chip">{item.source_title}</span>
        <span className="chip">priority {item.priority}</span>
      </div>
      <RichText
        text={item.extract_content ?? ''}
        className="max-h-[26rem] overflow-y-auto text-[0.9375rem] leading-7 text-slate-200"
      />
      <div className="mt-5 flex flex-wrap gap-2">
        <button className="btn btn-primary" onClick={() => navigate(`/read/${item.id}`)}>
          Work on this
        </button>
        <button className="btn" disabled={busy} onClick={() => postpone(3)}>
          Later (3d)
        </button>
        <button className="btn" disabled={busy} onClick={() => postpone(14)}>
          Much later (14d)
        </button>
        <button
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.scheduleExtract(item.id, { status: 'done' })
              onDone()
            } finally {
              setBusy(false)
            }
          }}
        >
          Done with it
        </button>
      </div>
    </div>
  )
}

/** Blitz Sprint Summary Scorecard Modal */
export function BlitzScorecardModal({
  stats,
  durationSec,
  onRestart,
  onClose,
}: {
  stats: {
    total: number
    correct: number
    avgLatencySec: number
    cpm: number
    automaticityRate: number
  }
  durationSec: number
  onRestart: (sec: number) => void
  onClose: () => void
}) {
  const accuracy = stats.total > 0 ? Math.round((stats.correct / stats.total) * 100) : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-xl border border-amber-500/40 bg-ink-card p-6 shadow-2xl space-y-5">
        <div className="text-center space-y-1">
          <div className="inline-flex px-3 py-1 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold uppercase tracking-wider text-amber-300 mb-1">
            Sprint Complete
          </div>
          <h2 className="text-xl font-bold text-slate-100">Sprint Complete!</h2>
          <p className="text-xs text-slate-400">{durationSec}s Memory Athlete Speed Run</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Cards Answered</p>
            <p className="font-mono text-2xl font-bold text-amber-300">{stats.total}</p>
            <p className="text-[0.625rem] text-slate-500">{stats.cpm} cards / min</p>
          </div>
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Accuracy</p>
            <p className={`font-mono text-2xl font-bold ${accuracy >= 85 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {accuracy}%
            </p>
            <p className="text-[0.625rem] text-slate-500">{stats.correct} correct</p>
          </div>
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Avg Reaction Time</p>
            <p className="font-mono text-2xl font-bold text-sky-300">
              {Math.floor(stats.avgLatencySec / 60)}m {Math.round(stats.avgLatencySec % 60)}s
            </p>
            <p className="text-[0.625rem] text-slate-500">per retrieval</p>
          </div>
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Automaticity Rate</p>
            <p className="font-mono text-2xl font-bold text-emerald-300">{stats.automaticityRate}%</p>
            <p className="text-[0.625rem] text-slate-500">reflexes &lt; 3.0s</p>
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn btn-primary flex-1 justify-center text-xs"
              onClick={() => onRestart(durationSec)}
            >
              Retry {durationSec}s Sprint
            </button>
            <button
              type="button"
              className="btn flex-1 justify-center text-xs"
              onClick={() => onRestart(durationSec === 30 ? 60 : 30)}
            >
              Switch to {durationSec === 30 ? '60s' : '30s'}
            </button>
          </div>
          <button type="button" className="btn justify-center text-xs text-slate-400" onClick={onClose}>
            Return to Normal Review
          </button>
        </div>
      </div>
    </div>
  )
}
