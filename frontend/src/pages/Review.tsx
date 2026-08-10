import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Grade, QueueItem, SessionSummary, SubmitAnswerResponse } from '../api/types'
import { GRADES } from '../api/types'
import { OcclusionCard } from '../components/Occlusion'
import { Empty, ErrorNote, RichText, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

const GRADE_STYLE: Record<Grade, string> = {
  again: 'border-rose-500/40 text-rose-300 hover:bg-rose-500/15',
  hard: 'border-amber-500/40 text-amber-300 hover:bg-amber-500/15',
  good: 'border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/15',
  easy: 'border-sky-500/40 text-sky-300 hover:bg-sky-500/15',
}

/** The unified session view (§9): one endpoint hands back cards *and* extracts,
 *  so this page routes on `kind` rather than the user picking a mode. */
export default function Review() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [item, setItem] = useState<QueueItem | null>(null)
  const [session, setSession] = useState<SessionSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  const [answer, setAnswer] = useState('')
  const [grading, setGrading] = useState(false)
  const [result, setResult] = useState<SubmitAnswerResponse | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [lastOutcome, setLastOutcome] = useState<string | null>(null)

  const shownAt = useRef<number>(Date.now())
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [next, summary] = await Promise.all([api.nextItem(), api.session()])
      setItem(next)
      setSession(summary)
      setAnswer('')
      setResult(null)
      setRevealed(false)
      shownAt.current = Date.now()
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (item?.kind === 'card' && !revealed) inputRef.current?.focus()
  }, [item, revealed])

  const llmEnabled = Boolean(user?.llm_grading_consent && user?.has_api_key)

  async function grade() {
    if (!item || item.kind !== 'card') return
    const latency = Date.now() - shownAt.current
    setGrading(true)
    setError(null)
    try {
      const graded = await api.submitAnswer(item.id, answer, latency)
      setResult(graded)
      setRevealed(true)
    } catch (err) {
      setError(err)
    } finally {
      setGrading(false)
    }
  }

  function reveal() {
    setRevealed(true)
    setResult(null)
  }

  async function confirm(finalGrade: Grade) {
    if (!item || item.kind !== 'card') return
    const overridden = Boolean(result && !result.degraded_to_manual && result.suggested_grade !== finalGrade)
    try {
      const outcome = await api.confirmReview(
        item.id,
        finalGrade,
        overridden,
        answer || undefined,
        Date.now() - shownAt.current,
      )
      setLastOutcome(
        `${finalGrade} — next in ${formatInterval(outcome.interval_days)}${
          outcome.leech_flagged ? ' · flagged as a leech' : ''
        }`,
      )
      await load()
    } catch (err) {
      setError(err)
    }
  }

  // Keyboard: 1-4 grade after reveal, Ctrl/Cmd+Enter submits the typed answer.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!item || item.kind !== 'card') return
      if (revealed && e.key >= '1' && e.key <= '4') {
        e.preventDefault()
        void confirm(GRADES[Number(e.key) - 1])
      }
      if (!revealed && e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        void (llmEnabled && answer.trim() ? grade() : reveal())
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (loading) return <Spinner label="Composing your session…" />
  if (error && !item) return <ErrorNote error={error} />

  if (!item) {
    return (
      <div className="space-y-6">
        <SessionHeader session={session} />
        <Empty title="Nothing due right now.">
          <p>
            Your queue is empty for today. Add cards, import a deck, or bring in something to read.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <button className="btn" onClick={() => navigate('/decks')}>
              Add cards
            </button>
            <button className="btn" onClick={() => navigate('/read')}>
              Add reading
            </button>
          </div>
        </Empty>
      </div>
    )
  }

  if (item.kind === 'extract') {
    return (
      <div className="space-y-6">
        <SessionHeader session={session} outcome={lastOutcome} />
        <ExtractCard item={item} onDone={load} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <SessionHeader session={session} outcome={lastOutcome} />

      <div className="card">
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="chip">{item.deck_name}</span>
          <span className="chip">{item.state}</span>
          {item.grading_profile && <span className="chip">{item.grading_profile}</span>}
          <span className="chip">priority {item.priority}</span>
        </div>

        {item.occlusion ? (
          <div className="space-y-3">
            {item.occlusion.header && (
              <p className="text-lg leading-relaxed text-slate-100">{item.occlusion.header}</p>
            )}
            <OcclusionCard payload={item.occlusion} revealed={revealed} />
          </div>
        ) : (
          <RichText text={item.front ?? ''} className="text-lg leading-relaxed text-slate-100" />
        )}

        {!revealed && (
          <div className="mt-6">
            <label className="label" htmlFor="answer">
              {llmEnabled ? 'Type your answer' : 'Type your answer (optional — grading is manual)'}
            </label>
            <textarea
              id="answer"
              ref={inputRef}
              className="input min-h-[7rem] resize-y"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Recall it from memory, then commit…"
            />
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {llmEnabled ? (
                <button
                  className="btn btn-primary"
                  onClick={grade}
                  disabled={grading || !answer.trim()}
                >
                  {grading ? 'Grading…' : 'Submit answer'}
                </button>
              ) : null}
              <button className="btn" onClick={reveal} disabled={grading}>
                {llmEnabled ? 'Skip grading, just show me' : 'Show answer'}
              </button>
              <span className="text-xs text-slate-600">⌘/Ctrl + Enter</span>
            </div>
            {!llmEnabled && (
              <p className="mt-3 text-xs text-slate-600">
                LLM grading is off. Turn it on in{' '}
                <button className="underline hover:text-slate-400" onClick={() => navigate('/settings')}>
                  Settings
                </button>{' '}
                by adding a Google API key and giving consent.
              </p>
            )}
          </div>
        )}

        {revealed && (
          <div className="mt-6 space-y-4">
            <div className="rounded-lg border border-ink-line bg-ink p-4">
              <p className="label">Reference answer</p>
              <RichText
                text={
                  result?.reference_answer ||
                  (item.occlusion ? 'The highlighted region is outlined above.' : '')
                }
                className="text-slate-200"
              />
            </div>

            {result && !result.degraded_to_manual && <GradeReasoning result={result} />}
            {result?.degraded_to_manual && result.degraded_reason !== 'consent_not_given' && (
              <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                Automatic grading was unavailable ({result.degraded_reason}). Grade it yourself —
                your scheduling is unaffected.
              </div>
            )}

            <div>
              <p className="label">
                {result && !result.degraded_to_manual
                  ? result.needs_confirmation
                    ? 'Confirm or correct the grade'
                    : 'Accept the suggestion, or override'
                  : 'How well did you recall it?'}
              </p>
              <div className="flex flex-wrap gap-2">
                {GRADES.map((g, i) => {
                  const suggested =
                    result && !result.degraded_to_manual && result.suggested_grade === g
                  return (
                    <button
                      key={g}
                      onClick={() => confirm(g)}
                      className={`btn ${GRADE_STYLE[g]} ${
                        suggested ? 'ring-1 ring-inset ring-current' : ''
                      }`}
                    >
                      <span className="capitalize">{g}</span>
                      <span className="text-xs opacity-50">{i + 1}</span>
                      {suggested && <span className="text-xs opacity-70">· suggested</span>}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      <ErrorNote error={error} />
    </div>
  )
}

/** §4.1 step 5: show the grade *and* the reasoning, so the model is auditable. */
function GradeReasoning({ result }: { result: SubmitAnswerResponse }) {
  const pct = Math.round(result.confidence * 100)
  return (
    <div className="rounded-lg border border-ink-line bg-ink p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`chip capitalize ${GRADE_STYLE[result.suggested_grade]}`}>
          {result.suggested_grade}
        </span>
        <span className="chip">{pct}% confident</span>
        {result.model_used && <span className="chip">{result.model_used}</span>}
        {result.cached && <span className="chip">cached</span>}
        {result.heuristic_overlap !== null && (
          <span className="chip">keyword overlap {Math.round(result.heuristic_overlap * 100)}%</span>
        )}
      </div>

      {result.reasoning && <p className="mt-3 text-sm text-slate-300">{result.reasoning}</p>}

      {(result.matched_points.length > 0 || result.missed_points.length > 0) && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {result.matched_points.length > 0 && (
            <div>
              <p className="label">Got</p>
              <ul className="space-y-1 text-sm text-emerald-300/90">
                {result.matched_points.map((p, i) => (
                  <li key={i}>✓ {p}</li>
                ))}
              </ul>
            </div>
          )}
          {result.missed_points.length > 0 && (
            <div>
              <p className="label">Missed</p>
              <ul className="space-y-1 text-sm text-amber-300/90">
                {result.missed_points.map((p, i) => (
                  <li key={i}>· {p}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {result.needs_confirmation && (
        <p className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          This grade disagreed with the keyword check, or the model wasn't confident — worth a
          second look before you accept it.
        </p>
      )}
    </div>
  )
}

/** IR extracts surfaced inside the review session (§9.4). */
function ExtractCard({ item, onDone }: { item: QueueItem; onDone: () => void }) {
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
        className="max-h-[26rem] overflow-y-auto text-[15px] leading-7 text-slate-200"
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

function SessionHeader({
  session,
  outcome,
}: {
  session: SessionSummary | null
  outcome?: string | null
}) {
  if (!session) return null
  const { counts, caps } = session
  const planned = (counts.review ?? 0) + (counts.new ?? 0) + (counts.ir ?? 0)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="chip">{counts.review ?? 0} reviews</span>
        <span className="chip">{counts.new ?? 0} new</span>
        <span className="chip">{counts.ir ?? 0} reading</span>
        <span className="chip">~{Math.round(session.budget_seconds / 60)} min budget</span>
        {caps.reviews_done_today > 0 && (
          <span className="chip">{caps.reviews_done_today} done today</span>
        )}
        {planned === 0 && <span className="chip">queue clear</span>}
      </div>

      {outcome && <p className="text-xs text-slate-500">Last: {outcome}</p>}

      {/* §3.1: guardrails must be visible, or a smoothed backlog looks like a bug. */}
      {session.notes.map((note, i) => (
        <p
          key={i}
          className="rounded-lg border border-sky-500/25 bg-sky-500/5 px-3 py-2 text-xs text-sky-200/90"
        >
          {note}
        </p>
      ))}
    </div>
  )
}

function formatInterval(days: number): string {
  if (days < 1 / 24) return `${Math.max(1, Math.round(days * 1440))} min`
  if (days < 1) return `${Math.round(days * 24)} h`
  if (days < 30) return `${Math.round(days)} d`
  if (days < 365) return `${(days / 30).toFixed(1)} mo`
  return `${(days / 365).toFixed(1)} y`
}
