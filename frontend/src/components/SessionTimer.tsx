import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Bank, StudySession } from '../api/types'

/** A study-session countdown that flashes rainbow when time is up, and banks
 *  the time you save by finishing your card target early.
 *
 *  The countdown lives in localStorage as an absolute `endsAt` timestamp
 *  rather than a ticking counter in React state. That keeps the clock correct
 *  across everything that actually happens during a session: the Review tree
 *  remounting between cards, a page reload, a tab left in the background
 *  where timers get throttled, or navigating to Decks and back.
 *
 *  The *session* — goal, target, banked time — lives on the server, because a
 *  bank that evaporates when browser storage is cleared isn't a record of
 *  anything. The two are linked by `sessionId` so a reload rejoins the open
 *  session instead of orphaning it.
 */

const STORAGE_KEY = 'memorization.timer'

/** Fired by the Review page after a card is graded, so the session's progress
 *  chip updates without this component polling the bank on a timer. */
export const REVIEW_EVENT = 'memorization:reviewed'

interface Persisted {
  durationMin: number
  /** Epoch ms the countdown ends at; null when idle. */
  endsAt: number | null
  /** Ms left at the moment of pausing; null unless paused. */
  pausedMs: number | null
  /** The server-side session this countdown belongs to, if any. */
  sessionId: string | null
}

const DEFAULTS: Persisted = {
  durationMin: 45,
  endsAt: null,
  pausedMs: null,
  sessionId: null,
}

interface Preset {
  label: string
  minutes: number[]
  /** Hour range [start, end) in local time this preset is suggested for. */
  from: number
  to: number
}

// Longer blocks in the morning, shorter as the day wears on.
const PRESETS: Preset[] = [
  { label: 'Morning', minutes: [75, 90], from: 4, to: 12 },
  { label: 'Afternoon', minutes: [45, 60], from: 12, to: 17 },
  { label: 'Evening', minutes: [25, 30], from: 17, to: 28 },
]

/** Which preset today's clock suggests. Evening wraps past midnight (17:00 to
 *  04:00), so late-night hours resolve to the short blocks rather than to
 *  "morning" on a technicality. */
export function presetForHour(hour: number): Preset {
  const wrapped = hour < 4 ? hour + 24 : hour
  return PRESETS.find((p) => wrapped >= p.from && wrapped < p.to) ?? PRESETS[1]
}

function load(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULTS, durationMin: presetForHour(new Date().getHours()).minutes[0] }
    const parsed = JSON.parse(raw) as Partial<Persisted>
    return {
      durationMin:
        typeof parsed.durationMin === 'number' && parsed.durationMin > 0
          ? parsed.durationMin
          : DEFAULTS.durationMin,
      endsAt: typeof parsed.endsAt === 'number' ? parsed.endsAt : null,
      pausedMs: typeof parsed.pausedMs === 'number' ? parsed.pausedMs : null,
      sessionId: typeof parsed.sessionId === 'string' ? parsed.sessionId : null,
    }
  } catch {
    return DEFAULTS
  }
}

function save(state: Persisted) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    /* private mode / quota — the timer still works for this page view */
  }
}

export function formatClock(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`
}

/** Banked time reads as a rounded human duration — "2h 15m saved" — since
 *  nobody cares about the seconds on a number they're accumulating. */
export function formatBanked(seconds: number): string {
  if (seconds <= 0) return '0m'
  // Under a minute reads as seconds: rounding 8s up to "1m" overstates a
  // number the user is accumulating, which is the one direction that matters.
  if (seconds < 60) return `${Math.round(seconds)}s`
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  if (h > 0) return m > 0 ? `${h}h ${m}m` : `${h}h`
  return `${Math.max(1, m)}m`
}

export default function SessionTimer() {
  const [state, setState] = useState<Persisted>(load)
  const [now, setNow] = useState(() => Date.now())
  const [planning, setPlanning] = useState(false)
  const [bank, setBank] = useState<Bank | null>(null)
  const [justFinished, setJustFinished] = useState<StudySession | null>(null)
  const [busy, setBusy] = useState(false)

  // Post-session reflection (§2): the exit half of the focus-goal prompt.
  // Reset whenever a new session finishes, since it's per-block, not global.
  const [reflectDistraction, setReflectDistraction] = useState('')
  const [reflectPlan, setReflectPlan] = useState('')
  const [reflectSaving, setReflectSaving] = useState(false)
  const [reflectSaved, setReflectSaved] = useState(false)

  useEffect(() => {
    setReflectDistraction('')
    setReflectPlan('')
    setReflectSaved(false)
  }, [justFinished?.id])

  async function saveReflection() {
    if (!justFinished) return
    setReflectSaving(true)
    try {
      await api.reflectOnSession(justFinished.id, reflectDistraction, reflectPlan)
      setReflectSaved(true)
    } catch {
      /* a nicety, not a requirement — don't trap the user in an error over it */
    } finally {
      setReflectSaving(false)
    }
  }

  const running = state.endsAt !== null && state.pausedMs === null
  const remainingMs = state.pausedMs ?? (state.endsAt !== null ? state.endsAt - now : null)
  const finished = state.endsAt !== null && state.pausedMs === null && (remainingMs ?? 1) <= 0
  const idle = state.endsAt === null

  useEffect(() => save(state), [state])

  const refreshBank = useCallback(async () => {
    try {
      setBank(await api.bank())
    } catch {
      /* the countdown works without the bank; don't block study on it */
    }
  }, [])

  useEffect(() => {
    void refreshBank()
  }, [refreshBank])

  // Progress toward the card target changes exactly when a card is graded, so
  // Review announces it rather than this component polling for it.
  useEffect(() => {
    const onReviewed = () => void refreshBank()
    window.addEventListener(REVIEW_EVENT, onReviewed)
    return () => window.removeEventListener(REVIEW_EVENT, onReviewed)
  }, [refreshBank])

  // Only tick while a countdown is actually live. Once finished the display is
  // pinned at 0:00, so there's nothing left to re-render for.
  useEffect(() => {
    if (!running || finished) return
    const id = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(id)
  }, [running, finished])

  // Resync the moment the tab regains focus: background throttling means the
  // interval above may not have fired for minutes.
  useEffect(() => {
    const resync = () => setNow(Date.now())
    window.addEventListener('visibilitychange', resync)
    window.addEventListener('focus', resync)
    return () => {
      window.removeEventListener('visibilitychange', resync)
      window.removeEventListener('focus', resync)
    }
  }, [])

  /** Bank the server-side session. Deliberately does NOT touch the countdown:
   *  when the clock runs out this fires automatically, and clearing `endsAt`
   *  here would flip `finished` back to false and kill the rainbow flash
   *  before it ever rendered. */
  const settleSession = useCallback(
    async (remaining: number) => {
      const id = state.sessionId
      if (!id) return
      setState((s) => ({ ...s, sessionId: null }))
      setBusy(true)
      try {
        setJustFinished(await api.finishSession(id, Math.max(0, Math.round(remaining / 1000))))
        await refreshBank()
      } catch {
        /* the block is over either way; don't trap the user in an error */
      } finally {
        setBusy(false)
      }
    },
    [state.sessionId, refreshBank],
  )

  /** End the block outright: settle it and clear the clock. */
  const endBlock = useCallback(
    async (remaining: number) => {
      await settleSession(remaining)
      setState((s) => ({ ...s, endsAt: null, pausedMs: null, sessionId: null }))
    },
    [settleSession],
  )

  // The countdown reaching zero banks the session on its own — otherwise a
  // block you walked away from would never settle. The clock is left showing
  // 0:00 and flashing until you acknowledge it.
  useEffect(() => {
    if (finished && state.sessionId && !busy) void settleSession(0)
  }, [finished, state.sessionId, busy, settleSession])

  const begin = useCallback(
    async (minutes: number, goalCards: number, focusGoal: string) => {
      setJustFinished(null)
      setBusy(true)
      try {
        const session = await api.startSession({
          planned_minutes: minutes,
          goal_cards: goalCards,
          focus_goal: focusGoal.trim() || null,
        })
        setNow(Date.now())
        setState({
          durationMin: minutes,
          endsAt: Date.now() + minutes * 60_000,
          pausedMs: null,
          sessionId: session.id,
        })
        await refreshBank()
      } catch {
        // Fall back to a plain countdown: an unreachable backend shouldn't
        // stop you studying, it just means this block earns nothing.
        setNow(Date.now())
        setState({
          durationMin: minutes,
          endsAt: Date.now() + minutes * 60_000,
          pausedMs: null,
          sessionId: null,
        })
      } finally {
        setBusy(false)
        setPlanning(false)
      }
    },
    [refreshBank],
  )

  const pause = useCallback(() => {
    setState((s) =>
      s.endsAt === null || s.pausedMs !== null
        ? s
        : { ...s, pausedMs: Math.max(0, s.endsAt - Date.now()) },
    )
  }, [])

  const resume = useCallback(() => {
    setNow(Date.now())
    setState((s) =>
      s.pausedMs === null ? s : { ...s, endsAt: Date.now() + s.pausedMs, pausedMs: null },
    )
  }, [])

  const current = bank?.current ?? null
  const bankedToday = bank?.today_seconds ?? 0

  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-baseline gap-3">
          <span
            className={`font-mono text-3xl tabular-nums ${
              finished ? 'timer-finished' : idle ? 'text-slate-600' : 'text-slate-100'
            }`}
            role="timer"
            aria-live={finished ? 'assertive' : 'off'}
          >
            {finished ? '0:00' : formatClock(remainingMs ?? state.durationMin * 60_000)}
          </span>
          {finished ? (
            <span className="text-sm font-medium text-slate-300">Time's up</span>
          ) : (
            <span className="text-xs text-slate-600">
              {idle ? `${state.durationMin} min block` : running ? 'counting down' : 'paused'}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {bankedToday > 0 && (
            <span
              className="chip border-emerald-500/40 text-emerald-300"
              title="Time earned back today by hitting your targets early"
            >
              🏦 {formatBanked(bankedToday)} banked today
            </span>
          )}
          {idle && (
            <button
              className="btn btn-primary"
              disabled={busy}
              onClick={() => setPlanning((p) => !p)}
            >
              {planning ? 'Cancel' : 'Start a block'}
            </button>
          )}
          {running && !finished && (
            <button className="btn" onClick={pause}>
              Pause
            </button>
          )}
          {state.pausedMs !== null && (
            <button className="btn btn-primary" onClick={resume}>
              Resume
            </button>
          )}
          {!idle && (
            <button
              className="btn"
              disabled={busy}
              onClick={() => void endBlock(remainingMs ?? 0)}
            >
              {finished ? 'Close' : 'End block'}
            </button>
          )}
        </div>
      </div>

      {/* The live goal, so the target you committed to stays in front of you
          rather than being a thing you typed once and forgot. */}
      {current && !idle && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-ink-line pt-3 text-xs">
          {current.focus_goal && (
            <span className="text-slate-300">🎯 {current.focus_goal}</span>
          )}
          {current.goal_cards > 0 ? (
            <span
              className={`chip ${current.goal_met ? 'border-emerald-500/40 text-emerald-300' : ''}`}
            >
              {current.goal_met ? '✓ ' : ''}
              {current.cards_reviewed}/{current.goal_cards} cards
            </span>
          ) : (
            <span className="chip text-slate-600">no target — nothing to bank</span>
          )}
          {current.goal_met && !finished && (
            <span className="text-emerald-300">
              target hit — end the block now to bank {formatBanked(Math.max(0, remainingMs ?? 0) / 1000)}
            </span>
          )}
        </div>
      )}

      {justFinished && (
        <div
          className={`mt-3 rounded-lg border px-4 py-3 text-sm ${
            justFinished.banked_seconds > 0
              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'
              : 'border-ink-line text-slate-400'
          }`}
        >
          {justFinished.banked_seconds > 0 ? (
            <>
              Target hit with time to spare — <strong>{formatBanked(justFinished.banked_seconds)}</strong>{' '}
              banked. {justFinished.cards_reviewed} cards in{' '}
              {formatBanked(justFinished.active_seconds)}.
            </>
          ) : justFinished.goal_cards === 0 ? (
            <>Block done — {justFinished.cards_reviewed} cards reviewed.</>
          ) : (
            <>
              {justFinished.cards_reviewed} of {justFinished.goal_cards} cards — target missed, so
              nothing banked this time.
            </>
          )}
          <button
            className="ml-2 underline hover:text-slate-200"
            onClick={() => setJustFinished(null)}
          >
            dismiss
          </button>

          {reflectSaved ? (
            <p className="mt-2 text-xs text-slate-500">Reflection saved.</p>
          ) : (
            <div className="mt-3 space-y-2 border-t border-ink-line/60 pt-3">
              <input
                className="input py-1 text-xs"
                placeholder="What distracted you? (optional)"
                value={reflectDistraction}
                onChange={(e) => setReflectDistraction(e.target.value)}
              />
              <input
                className="input py-1 text-xs"
                placeholder="How will you fix it next time? (optional)"
                value={reflectPlan}
                onChange={(e) => setReflectPlan(e.target.value)}
              />
              <button
                className="btn px-2.5 py-1 text-xs"
                disabled={reflectSaving}
                onClick={saveReflection}
              >
                {reflectSaving ? 'Saving…' : 'Save reflection'}
              </button>
            </div>
          )}
        </div>
      )}

      {planning && <PlanBlock defaultMinutes={state.durationMin} busy={busy} onStart={begin} />}
    </div>
  )
}

/** The pre-session micro-goal prompt: one specific thing to master, a
 *  duration, and the card target that decides whether time gets banked. */
function PlanBlock({
  defaultMinutes,
  busy,
  onStart,
}: {
  defaultMinutes: number
  busy: boolean
  onStart: (minutes: number, goalCards: number, focusGoal: string) => void
}) {
  const [minutes, setMinutes] = useState(defaultMinutes)
  const [goalCards, setGoalCards] = useState('')
  const [focusGoal, setFocusGoal] = useState('')
  const [suggested, setSuggested] = useState<number | null>(null)

  const preset = presetForHour(new Date().getHours())

  // Suggest the target from what the queue actually plans to show — a number
  // pulled from thin air is one you'd learn to ignore.
  useEffect(() => {
    let cancelled = false
    api
      .session()
      .then((s) => {
        if (cancelled) return
        const planned = (s.counts.review ?? 0) + (s.counts.new ?? 0)
        setSuggested(planned)
        setGoalCards((g) => (g === '' && planned > 0 ? String(planned) : g))
      })
      .catch(() => {
        /* suggestion is a nicety, not a requirement */
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="mt-4 space-y-4 border-t border-ink-line pt-4">
      <div>
        <label className="label" htmlFor="focus-goal">
          What one thing will you master in this block?
        </label>
        <input
          id="focus-goal"
          className="input"
          placeholder="e.g. the Krebs cycle intermediates — optional"
          value={focusGoal}
          autoFocus
          onChange={(e) => setFocusGoal(e.target.value)}
        />
      </div>

      <div>
        <p className="label">How long?</p>
        <div className="space-y-2">
          {PRESETS.map((p) => (
            <div key={p.label} className="flex flex-wrap items-center gap-2">
              <span
                className={`w-20 shrink-0 text-xs ${
                  p === preset ? 'text-sky-300' : 'text-slate-600'
                }`}
              >
                {p.label}
              </span>
              {p.minutes.map((m) => (
                <button
                  key={m}
                  className={`btn px-2.5 py-1 text-xs ${
                    minutes === m ? 'border-sky-500/40 text-sky-200' : ''
                  }`}
                  onClick={() => setMinutes(m)}
                >
                  {m} min
                </button>
              ))}
              {p === preset && <span className="text-xs text-slate-600">← suggested now</span>}
            </div>
          ))}
          <div className="flex items-center gap-2 pt-1">
            <span className="w-20 shrink-0 text-xs text-slate-600">Custom</span>
            <input
              type="number"
              min={1}
              max={600}
              className="input w-24 py-1 text-xs"
              value={minutes}
              onChange={(e) => setMinutes(Math.max(1, Math.min(600, Number(e.target.value) || 1)))}
            />
            <span className="text-xs text-slate-600">min</span>
          </div>
        </div>
      </div>

      <div>
        <label className="label" htmlFor="goal-cards">
          Card target — hit it early and the rest of the block is banked
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <input
            id="goal-cards"
            type="number"
            min={0}
            max={10000}
            className="input w-24 py-1 text-sm"
            placeholder="0"
            value={goalCards}
            onChange={(e) => setGoalCards(e.target.value)}
          />
          {suggested !== null && suggested > 0 && (
            <button
              className="btn px-2 py-1 text-xs"
              onClick={() => setGoalCards(String(suggested))}
            >
              use today's {suggested}
            </button>
          )}
          <span className="text-xs text-slate-600">0 = untimed practice, banks nothing</span>
        </div>
      </div>

      <button
        className="btn btn-primary"
        disabled={busy}
        onClick={() => onStart(minutes, Math.max(0, Number(goalCards) || 0), focusGoal)}
      >
        {busy ? 'Starting…' : `Start ${minutes} min block`}
      </button>
    </div>
  )
}
