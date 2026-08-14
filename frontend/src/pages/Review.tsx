import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type {
  CardReference,
  Grade,
  Lesson,
  QueueItem,
  SessionSummary,
  SocraticTurn,
  StuckAlert,
  SubmitAnswerResponse,
} from '../api/types'
import { GRADES } from '../api/types'
import { OcclusionCard } from '../components/Occlusion'
import SessionTimer, { formatClock, REVIEW_EVENT } from '../components/SessionTimer'
import { Empty, ErrorNote, RichText, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

const LEARN_MODE_KEY = 'memorization.learnMode'

// Mirrors the backend's SCORE_BANDS (grading_service.py) — display only; the
// server is the one source of truth for which band a score actually lands in.
const GRADE_BAND: Record<Grade, string> = {
  again: '0–39%',
  hard: '40–69%',
  good: '70–89%',
  easy: '90–100%',
}

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
  // `?branch=<node id>` restricts the session to one knowledge-tree branch.
  const [params, setParams] = useSearchParams()
  const branch = params.get('branch')

  const [item, setItem] = useState<QueueItem | null>(null)
  const [session, setSession] = useState<SessionSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  const [answer, setAnswer] = useState('')
  const [grading, setGrading] = useState(false)
  const [result, setResult] = useState<SubmitAnswerResponse | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [lastOutcome, setLastOutcome] = useState<string | null>(null)

  // Stuck-state detector: a real-time nudge, not a per-card verdict — it
  // persists across the card transition below rather than being cleared by
  // `load()`, so it survives until the user acts on or dismisses it.
  const [stuckAlert, setStuckAlert] = useState<StuckAlert | null>(null)
  const [breakUntil, setBreakUntil] = useState<number | null>(null)

  // Learn & Practice: read a lesson built from the card's citations before
  // being asked the question.
  const [learnMode, setLearnMode] = useState(
    () => localStorage.getItem(LEARN_MODE_KEY) === '1',
  )
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [lessonLoading, setLessonLoading] = useState(false)
  const [taught, setTaught] = useState(false)

  // Socratic AI Guide: one diagnostic question at a time, never the answer.
  // Stateless on the server — the full history rides along with each turn.
  const [guideOpen, setGuideOpen] = useState(false)
  const [guideHistory, setGuideHistory] = useState<SocraticTurn[]>([])
  const [guideInput, setGuideInput] = useState('')
  const [guideLoading, setGuideLoading] = useState(false)
  const [guideDegraded, setGuideDegraded] = useState<string | null>(null)
  // The guide signalling "you've got it" — the cue to stop hinting and commit
  // an answer, which is the only way out of the loop that earns a grade.
  const [guideOnTrack, setGuideOnTrack] = useState(false)

  const shownAt = useRef<number>(Date.now())
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [next, summary] = await Promise.all([api.nextItem(branch), api.session(branch)])
      setItem(next)
      setSession(summary)
      setAnswer('')
      setResult(null)
      setRevealed(false)
      setLesson(null)
      setTaught(false)
      setGuideOpen(false)
      setGuideHistory([])
      setGuideInput('')
      setGuideDegraded(null)
      setGuideOnTrack(false)
      shownAt.current = Date.now()
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [branch])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (item?.kind === 'card' && !revealed) inputRef.current?.focus()
  }, [item, revealed])

  // Learn & Practice: fetch the lesson whenever a fresh card needs one — on
  // load, and immediately if the mode is switched on mid-card (before the
  // gate below has been passed for this card).
  useEffect(() => {
    if (!learnMode || !item || item.kind !== 'card' || taught) return
    let cancelled = false
    setLessonLoading(true)
    api
      .lesson(item.id)
      .then((l) => {
        if (!cancelled) setLesson(l)
      })
      .catch((err) => setError(err))
      .finally(() => {
        if (!cancelled) setLessonLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [learnMode, item, taught])

  function toggleLearnMode() {
    setLearnMode((prev) => {
      const next = !prev
      localStorage.setItem(LEARN_MODE_KEY, next ? '1' : '0')
      return next
    })
  }

  function continueToQuestion() {
    setTaught(true)
    // Lesson-reading time is not recall time — don't let it pollute the
    // informational latency note.
    shownAt.current = Date.now()
  }

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

  async function askGuide(message: string) {
    if (!item || item.kind !== 'card') return
    setGuideLoading(true)
    try {
      const resp = await api.guide(item.id, guideHistory, message)
      if (resp.degraded) {
        setGuideDegraded(resp.degraded_reason)
        return
      }
      const turns: SocraticTurn[] = [...guideHistory]
      if (message.trim()) turns.push({ role: 'student', text: message.trim() })
      turns.push({ role: 'guide', text: resp.message })
      setGuideHistory(turns)
      setGuideOnTrack(resp.on_track)
      setGuideInput('')
    } catch (err) {
      setError(err)
    } finally {
      setGuideLoading(false)
    }
  }

  function openGuide() {
    setGuideOpen(true)
    if (guideHistory.length === 0) void askGuide('')
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
      if (outcome.stuck_alert) setStuckAlert(outcome.stuck_alert)
      // Let the session timer refresh its progress toward the card target.
      window.dispatchEvent(new Event(REVIEW_EVENT))
      await load()
    } catch (err) {
      setError(err)
    }
  }

  // Keyboard: 1-4 grade after reveal, Ctrl/Cmd+Enter submits the typed answer.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!item || item.kind !== 'card') return
      // The break overlay hides the card entirely; without this, Ctrl+Enter
      // during a break would reveal or grade a card that isn't on screen.
      if (breakUntil) return
      // The lesson gate has no answer box to submit and no grade to confirm —
      // without this, Ctrl+Enter during the lesson silently reveals the
      // answer before the question is ever shown.
      if (learnMode && !taught) return
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

  const clearBranch = () => setParams((p) => {
    const next = new URLSearchParams(p)
    next.delete('branch')
    return next
  })

  // Branched in a helper rather than by returning early: `loading` flips true
  // on every card advance, and an early return there would unmount the session
  // timer between cards. It has to outlive the card it was started on.
  const renderBody = () => {
    if (loading) return <Spinner label="Composing your session…" />
    if (error && !item) return <ErrorNote error={error} />

    if (!item) {
      return (
        <div className="space-y-6">
          <SessionHeader session={session} branchActive={Boolean(branch)} onClearBranch={clearBranch} learnMode={learnMode} onToggleLearnMode={toggleLearnMode} />
          <Empty title={branch ? 'Nothing due in this branch.' : 'Nothing due right now.'}>
            <p>
              {branch
                ? 'This branch is caught up. Study everything, or add more under it in the Tree.'
                : 'Your queue is empty for today. Add cards, import a deck, or bring in something to read.'}
            </p>
            <div className="mt-4 flex justify-center gap-2">
              {branch ? (
                <button className="btn" onClick={clearBranch}>
                  Study everything
                </button>
              ) : (
                <>
                  <button className="btn" onClick={() => navigate('/decks')}>
                    Add cards
                  </button>
                  <button className="btn" onClick={() => navigate('/read')}>
                    Add reading
                  </button>
                </>
              )}
            </div>
          </Empty>
        </div>
      )
    }

    if (item.kind === 'extract') {
      return (
        <div className="space-y-6">
          <SessionHeader session={session} outcome={lastOutcome} branchActive={Boolean(branch)} onClearBranch={clearBranch} learnMode={learnMode} onToggleLearnMode={toggleLearnMode} />
          <ExtractCard item={item} onDone={load} />
        </div>
      )
    }

    if (learnMode && !taught) {
      return (
        <div className="space-y-6">
          <SessionHeader session={session} outcome={lastOutcome} branchActive={Boolean(branch)} onClearBranch={clearBranch} learnMode={learnMode} onToggleLearnMode={toggleLearnMode} />
          <LessonGate
            lesson={lesson}
            loading={lessonLoading}
            deckName={item.deck_name}
            onContinue={continueToQuestion}
            onOpenSettings={() => navigate('/settings')}
          />
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <SessionHeader session={session} outcome={lastOutcome} branchActive={Boolean(branch)} onClearBranch={clearBranch} learnMode={learnMode} onToggleLearnMode={toggleLearnMode} />

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
                {llmEnabled && !guideOpen && (
                  <button className="btn" onClick={openGuide}>
                    💬 Stuck? Ask your Guide
                  </button>
                )}
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
              {guideOpen && (
                <SocraticGuide
                  history={guideHistory}
                  input={guideInput}
                  onInputChange={setGuideInput}
                  loading={guideLoading}
                  degraded={guideDegraded}
                  onTrack={guideOnTrack}
                  onSend={() => void askGuide(guideInput)}
                  onClose={() => setGuideOpen(false)}
                  onCommit={() => {
                    setGuideOpen(false)
                    inputRef.current?.focus()
                  }}
                />
              )}
            </div>
          )}

          {revealed && (
            <div className="mt-6 space-y-4">
              <div className="rounded-lg border border-ink-line bg-ink p-4">
                <p className="label">Reference answer</p>
                <RichText
                  text={result?.reference_answer || item.back || ''}
                  className="text-slate-200"
                />
              </div>

              {result?.latency_note && (
                <p className="text-xs text-slate-600" title="Informational only — never affects the grade">
                  ⏱ {result.latency_note}
                </p>
              )}

              <ReferenceReadings references={item.references} />

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
                        <span className="text-xs opacity-50">{GRADE_BAND[g]}</span>
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

  return (
    <div className="space-y-6">
      <SessionTimer />
      {stuckAlert && !breakUntil && (
        <StuckBanner
          alert={stuckAlert}
          onBreak={() => {
            setBreakUntil(Date.now() + stuckAlert.suggested_break_minutes * 60_000)
            setStuckAlert(null)
          }}
          onDismiss={() => setStuckAlert(null)}
        />
      )}
      {breakUntil ? (
        <BreakOverlay until={breakUntil} onDone={() => setBreakUntil(null)} />
      ) : (
        renderBody()
      )}
    </div>
  )
}

/** Stuck-state detector (§ Stuck-state detector): the backend flags an
 *  accuracy slump or a latency spike on `confirm`; this is the nudge — take
 *  it as a prompt to break or work, never a silent behavior change, matching
 *  how every other automatic suggestion in this app stays a proposal. */
function StuckBanner({
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
      <p>⚠ {alert.message}</p>
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
function BreakOverlay({ until, onDone }: { until: number; onDone: () => void }) {
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
function SocraticGuide({
  history,
  input,
  onInputChange,
  loading,
  degraded,
  onTrack,
  onSend,
  onClose,
  onCommit,
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
        <p className="text-xs text-slate-600">
          Guide unavailable ({degraded === 'no_api_key' ? 'no API key set' : degraded}).
        </p>
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

/** Learn & Practice: the lesson gate shown before a card's question.
 *
 *  Built from the card's own citations, never invented — a card with none is
 *  plainly not teachable rather than getting a fabricated explanation. When
 *  grading is off the cited passage itself is shown, labelled as the raw
 *  source rather than a written lesson, mirroring how grading degrades.
 */
function LessonGate({
  lesson,
  loading,
  deckName,
  onContinue,
  onOpenSettings,
}: {
  lesson: Lesson | null
  loading: boolean
  deckName: string | null
  onContinue: () => void
  onOpenSettings: () => void
}) {
  return (
    <div className="card">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {deckName && <span className="chip">{deckName}</span>}
        <span className="chip text-sky-300">learn &amp; practice</span>
      </div>

      {loading || !lesson ? (
        <Spinner label="Preparing the lesson…" />
      ) : !lesson.available ? (
        <div className="space-y-3">
          <Empty title="Nothing to teach from for this card.">
            This card has no source citation — Learn &amp; Practice only works on cards
            generated from an uploaded document (Decks → Generate a deck from a document).
          </Empty>
          <button className="btn btn-primary" onClick={onContinue}>
            Skip straight to the question
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {!lesson.generated && (
            <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              {lesson.reason === 'consent_not_given' || lesson.reason === 'no_api_key' ? (
                <>
                  Showing the raw source passage — turn on LLM grading in{' '}
                  <button className="underline" onClick={onOpenSettings}>
                    Settings
                  </button>{' '}
                  for a written lesson instead.
                </>
              ) : (
                `Showing the raw source passage — lesson generation was unavailable (${lesson.reason}).`
              )}
            </p>
          )}

          <RichText
            text={lesson.body}
            className="text-[15px] leading-7 text-slate-200"
          />

          {lesson.key_points.length > 0 && (
            <div>
              <p className="label">Key points</p>
              <ul className="space-y-1 text-sm text-slate-300">
                {lesson.key_points.map((p, i) => (
                  <li key={i}>· {p}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2 border-t border-ink-line pt-3 text-xs">
            {lesson.citations.map((c, i) => (
              <span key={i} className="chip">
                {c.locator ?? c.source_title ?? 'source'}
              </span>
            ))}
            {lesson.generated && lesson.model_used && (
              <span className="chip">{lesson.model_used}</span>
            )}
            {lesson.cached && <span className="chip">cached</span>}
          </div>

          <button className="btn btn-primary" onClick={onContinue}>
            I've got it — quiz me
          </button>
        </div>
      )}
    </div>
  )
}

/** The reading a card came from, shown once the answer is revealed.
 *
 *  A verified quote is displayed as a quote; an unverified one was never
 *  stored, so what shows instead is the real passage — the guarantee being
 *  that anything presented in quotation marks genuinely appears in the source.
 */
function ReferenceReadings({ references }: { references: CardReference[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  if (!references || references.length === 0) return null

  return (
    <div className="rounded-lg border border-ink-line bg-ink p-4">
      <p className="label">
        {references.length > 1 ? 'Reference readings' : 'Reference reading'}
      </p>
      <div className="mt-2 space-y-4">
        {references.map((ref, i) => {
          const showingPassage = expanded.has(i) || !ref.quote
          return (
            <div key={i}>
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                {ref.locator && <span className="chip text-sky-300">{ref.locator}</span>}
                {ref.source_title && <span className="chip">{ref.source_title}</span>}
              </div>

              {ref.quote && !showingPassage ? (
                <blockquote className="border-l-2 border-sky-500/40 pl-3 text-sm italic leading-6 text-slate-300">
                  “{ref.quote}”
                </blockquote>
              ) : (
                ref.passage && (
                  <RichText
                    text={ref.passage}
                    className="max-h-64 overflow-y-auto border-l-2 border-ink-line pl-3 text-sm leading-6 text-slate-300"
                  />
                )
              )}

              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                {ref.quote && ref.passage && (
                  <button
                    className="text-slate-500 underline hover:text-slate-300"
                    onClick={() =>
                      setExpanded((prev) => {
                        const next = new Set(prev)
                        next.has(i) ? next.delete(i) : next.add(i)
                        return next
                      })
                    }
                  >
                    {showingPassage ? 'Show just the quote' : 'Show the full passage'}
                  </button>
                )}
                {ref.extract_id && (
                  <a
                    className="text-slate-500 underline hover:text-slate-300"
                    href={`/read/${ref.extract_id}`}
                  >
                    Open in Read
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** §4.1 step 5: show the score *and* the reasoning, so the model is auditable.
 *
 *  The score (0-100) is the actual grading feedback — correctness against key
 *  concepts and keyword match. The grade chip next to it is only the FSRS
 *  scheduling bucket that score landed in; "confidence" is a separate axis
 *  entirely (how sure the model is in its own score), so it's labelled to
 *  avoid being read as a second correctness number.
 */
function GradeReasoning({ result }: { result: SubmitAnswerResponse }) {
  const pct = Math.round(result.confidence * 100)
  return (
    <div className="rounded-lg border border-ink-line bg-ink p-4">
      <div className="flex flex-wrap items-center gap-2">
        {result.score !== null && (
          <span className={`chip text-base font-semibold ${GRADE_STYLE[result.suggested_grade]}`}>
            {Math.round(result.score)}%
          </span>
        )}
        <span className={`chip capitalize ${GRADE_STYLE[result.suggested_grade]}`}>
          {result.suggested_grade}
        </span>
        <span className="chip">model confidence {pct}%</span>
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
  branchActive,
  onClearBranch,
  learnMode,
  onToggleLearnMode,
}: {
  session: SessionSummary | null
  outcome?: string | null
  branchActive?: boolean
  onClearBranch?: () => void
  learnMode?: boolean
  onToggleLearnMode?: () => void
}) {
  if (!session) return null
  const { counts, caps } = session
  const planned = (counts.review ?? 0) + (counts.new ?? 0) + (counts.ir ?? 0)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {branchActive && (
          <span className="chip border-sky-500/40 text-sky-300">
            branch-scoped
            <button className="ml-2 underline" onClick={onClearBranch}>
              exit
            </button>
          </span>
        )}
        <span className="chip">{counts.review ?? 0} reviews</span>
        <span className="chip">{counts.new ?? 0} new</span>
        <span className="chip">{counts.ir ?? 0} reading</span>
        <span className="chip">~{Math.round(session.budget_seconds / 60)} min budget</span>
        {caps.reviews_done_today > 0 && (
          <span className="chip">{caps.reviews_done_today} done today</span>
        )}
        {planned === 0 && <span className="chip">queue clear</span>}
        {onToggleLearnMode && (
          <button
            className={`chip ml-auto transition ${
              learnMode ? 'border-sky-500/40 text-sky-300' : 'hover:text-slate-300'
            }`}
            onClick={onToggleLearnMode}
            title="Read a short lesson from the card's source before each question"
          >
            📖 Learn &amp; Practice {learnMode ? 'on' : 'off'}
          </button>
        )}
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
