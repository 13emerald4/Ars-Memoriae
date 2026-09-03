import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type {
  CodeProblemOut,
  CodeProblemSummary,
  Deck,
  RunCodeResponse,
  SubmitCodeResponse,
} from '../api/types'
import { CodeEditor } from '../components/CodeEditor'
import { CodeSocraticTutor } from '../components/CodeSocraticTutor'
import { CodeTestConsole } from '../components/CodeTestConsole'
import {
  ConcordanceReader,
  CONCORDANCE_ENABLED_STORAGE_KEY,
  getStoredConcordanceEnabled,
} from '../components/ConcordanceReader'
import { ErrorNote, Spinner } from '../components/ui'
import {
  READING_MODES,
  ReadingMode,
  estimateReadMinutes,
  filterEditorialByMode,
  sectionCount,
} from '../services/reading_mode'
import { getGuidingQuestions } from '../services/guiding_questions'

const READING_MODE_KEY = 'memorization.readingMode'

function loadReadingMode(): ReadingMode {
  try {
    const saved = localStorage.getItem(READING_MODE_KEY)
    if (saved === 'concise' || saved === 'normal' || saved === 'robust') return saved
  } catch {
    /* private mode / storage disabled — fall through to the default */
  }
  return 'normal'
}

const TRACKS = [
  { id: 'track_0_python_basics', label: '🟢 Track 0: Python Basics & Numerics (MIT 6.0001 Lec 1–3, Pset 1)', icon: '🐍' },
  { id: 'track_1_pythonic_fluency', label: '🔵 Track 1: Structured Types & Aliasing (MIT 6.0001 Lec 4–5, Pset 2)', icon: '⚡' },
  { id: 'track_2_data_structures', label: '🟣 Track 2: ADTs, Hash Tables & OOP (MIT 6.0001 Lec 8–9, Pset 5)', icon: '🧱' },
  { id: 'track_3_algorithmic_scaffolds', label: '🟡 Track 3: Recursion & Scaffolds (MIT 6.0001 Lec 6, Pset 3–4)', icon: '📐' },
  { id: 'track_4_custom_sorting', label: '🟠 Track 4: Divide-and-Conquer Sorting (MIT 6.0001 Lec 12)', icon: '🔀' },
  { id: 'track_5_bit_manipulation', label: '🔴 Track 5: Binary Encodings & Bits (MIT 6.0001 Numerics)', icon: '🔢' },
  { id: 'track_6_complexity_math', label: '🟤 Track 6: Asymptotic Complexity & Efficiency (MIT 6.0001 Lec 10–11)', icon: '⏱' },
  { id: 'track_7_testing_exceptions', label: '⚪ Track 7: Testing, Debugging & Exceptions (MIT 6.0001 Lec 7)', icon: '🧪' },
  { id: 'track_8_graphs', label: '🟩 Track 8: Graphs & Optimization (MIT 6.0002 / 6.0001 Adv)', icon: '🕸' },
]

export default function FundamentalsStudio() {
  const [activeTrack, setActiveTrack] = useState<string>('track_0_python_basics')
  const [drills, setDrills] = useState<CodeProblemSummary[]>([])
  const [selectedDrillSlug, setSelectedDrillSlug] = useState<string | null>(null)
  const [drillDetail, setDrillDetail] = useState<CodeProblemOut | null>(null)
  const [activeTab, setActiveTab] = useState<'textbook' | 'question' | 'socratic'>('textbook')

  const [code, setCode] = useState<string>('')
  const [decks, setDecks] = useState<Deck[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [runResult, setRunResult] = useState<RunCodeResponse | SubmitCodeResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [exportMsg, setExportMsg] = useState<string | null>(null)

  // Speed-run reflex timer
  const [timerSec, setTimerSec] = useState<number>(60)
  const [timerRunning, setTimerRunning] = useState<boolean>(false)

  // Fullscreen reading mode
  const [isFullscreenReading, setIsFullscreenReading] = useState<boolean>(false)

  // Guttag lesson depth: Concise / Normal / Robust (persisted across sessions)
  const [readingMode, setReadingMode] = useState<ReadingMode>(loadReadingMode)

  useEffect(() => {
    try {
      localStorage.setItem(READING_MODE_KEY, readingMode)
    } catch {
      /* storage unavailable — the choice just won't persist */
    }
  }, [readingMode])

  // Concordance term highlights on/off toggle (persisted across sessions)
  const [concordanceEnabled, setConcordanceEnabled] = useState<boolean>(getStoredConcordanceEnabled)

  useEffect(() => {
    try {
      localStorage.setItem(CONCORDANCE_ENABLED_STORAGE_KEY, String(concordanceEnabled))
    } catch {
      /* storage unavailable */
    }
  }, [concordanceEnabled])

  // Peek answer toggle for questions
  const [showPeekAnswer, setShowPeekAnswer] = useState<boolean>(false)

  // All-questions overview: every drill across every chapter, not just the active track
  const [allDrills, setAllDrills] = useState<CodeProblemSummary[]>([])
  const [showAllQuestions, setShowAllQuestions] = useState<boolean>(false)
  const [allQuestionsSearch, setAllQuestionsSearch] = useState<string>('')

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (isFullscreenReading) setIsFullscreenReading(false)
      else if (showAllQuestions) setShowAllQuestions(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isFullscreenReading, showAllQuestions])

  const loadDrills = useCallback(async () => {
    try {
      setLoading(true)
      const list = await api.listCodeProblems({ kind: 'fundamental', track: activeTrack })
      setDrills(list)
      if (list.length > 0) {
        // Keep the drill the user is on. handleSubmit re-runs this to refresh the
        // per-drill status dots, and resetting to list[0] there would bounce them
        // back to the first drill and discard the result they just earned.
        setSelectedDrillSlug((prev) =>
          prev && list.some((d) => d.slug === prev) ? prev : list[0].slug
        )
      } else {
        setDrillDetail(null)
      }
      const dList = await api.decks()
      setDecks(dList)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [activeTrack])

  useEffect(() => {
    void loadDrills()
  }, [loadDrills])

  // Every fundamental drill across every chapter, for the "All Questions" overview.
  // Independent of activeTrack so switching chapters doesn't refetch it.
  const loadAllDrills = useCallback(async () => {
    try {
      const list = await api.listCodeProblems({ kind: 'fundamental' })
      setAllDrills(list)
    } catch (err) {
      setError(err)
    }
  }, [])

  useEffect(() => {
    void loadAllDrills()
  }, [loadAllDrills])

  const openDrillFromOverview = (d: CodeProblemSummary) => {
    setActiveTrack(d.track ?? TRACKS[0].id)
    setSelectedDrillSlug(d.slug)
    setActiveTab('question')
    setShowAllQuestions(false)
  }

  // Fetch drill detail when slug changes
  useEffect(() => {
    if (!selectedDrillSlug) return
    let active = true
    api
      .getCodeProblem(selectedDrillSlug)
      .then((detail) => {
        if (!active) return
        setDrillDetail(detail)
        const starter = detail.starter_codes?.python || detail.starter_codes?.typescript || ''
        setCode(starter)
        setRunResult(null)
        setActiveTab('textbook')
        setShowPeekAnswer(false)
        setTimerSec(60)
        setTimerRunning(false)
      })
      .catch((err) => {
        if (active) setError(err)
      })
    return () => {
      active = false
    }
  }, [selectedDrillSlug])

  // Timer countdown
  useEffect(() => {
    let interval: any
    if (timerRunning && timerSec > 0) {
      interval = setInterval(() => setTimerSec((s) => s - 1), 1000)
    } else if (timerSec === 0) {
      setTimerRunning(false)
    }
    return () => clearInterval(interval)
  }, [timerRunning, timerSec])

  const handleRun = async () => {
    if (!drillDetail) return
    setRunning(true)
    setError(null)
    try {
      const res = await api.runCode(drillDetail.slug, {
        code,
        language: 'python',
      })
      setRunResult(res)
    } catch (err) {
      setError(err)
    } finally {
      setRunning(false)
    }
  }

  const handleSubmit = async () => {
    if (!drillDetail) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await api.submitCode(drillDetail.slug, {
        code,
        language: 'python',
      })
      setRunResult(res)
      void loadDrills()
      void loadAllDrills()
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const handleExportCard = async (deckId: string) => {
    if (!drillDetail) return
    try {
      const resp = await api.exportProblemToCard(drillDetail.slug, deckId)
      setExportMsg(resp.message)
      setTimeout(() => setExportMsg(null), 4000)
    } catch (err) {
      setError(err)
    }
  }

  if (loading && drills.length === 0) return <Spinner />

  const currentIndex = drills.findIndex((d) => d.slug === selectedDrillSlug)
  const isFailed = runResult && runResult.status !== 'Accepted'

  const lessonMarkdown = drillDetail?.editorial
    ? filterEditorialByMode(drillDetail.editorial, readingMode)
    : ''
  const lessonSections = drillDetail?.editorial
    ? sectionCount(drillDetail.editorial, readingMode)
    : { shown: 0, total: 0 }
  const lessonReadTime = lessonMarkdown ? estimateReadMinutes(lessonMarkdown) : ''
  const guidingQuestions = drillDetail
    ? getGuidingQuestions(drillDetail.slug, drillDetail.title, drillDetail.category)
    : []

  const renderGuidingQuestionsBox = (isCompact = false) => {
    if (!guidingQuestions || guidingQuestions.length === 0) return null

    return (
      <div
        className={`rounded-xl border border-sky-500/30 bg-gradient-to-br from-sky-950/40 via-[#0d1524] to-[#090e17] ${
          isCompact ? 'p-3.5' : 'p-5'
        } shadow-lg space-y-2.5`}
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sky-500/20 pb-2">
          <div className="flex items-center gap-2">
            <span className="text-base">🧠</span>
            <div>
              <h3 className="font-bold text-sky-200 text-xs tracking-wide">
                Core Questions to Ponder as You Read
              </h3>
              <p className="text-[10px] text-slate-400">
                Active Inquiry — reflect on these fundamental mechanisms and edge cases throughout the lesson:
              </p>
            </div>
          </div>
          <span className="chip border-sky-500/40 bg-sky-500/10 text-[10px] text-sky-300 font-semibold">
            Pre-Reading Focus
          </span>
        </div>

        <ul className="space-y-2 text-xs text-slate-200">
          {guidingQuestions.map((q, idx) => (
            <li
              key={idx}
              className="flex items-start gap-2.5 rounded-lg border border-sky-500/15 bg-black/25 p-2.5 transition hover:border-sky-500/35 hover:bg-black/40"
            >
              <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-sky-500/20 font-mono text-[10px] font-bold text-sky-300">
                {idx + 1}
              </span>
              <span className="leading-relaxed text-slate-200 font-medium">{q}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  const readingModeToggle = (size: 'sm' | 'md' = 'sm') => (
    <div
      className="flex items-center gap-0.5 rounded-lg border border-ink-line/80 bg-[#090d13] p-0.5"
      role="group"
      aria-label="Lesson reading depth"
    >
      {READING_MODES.map((m) => (
        <button
          key={m.id}
          onClick={() => setReadingMode(m.id)}
          title={m.hint}
          aria-pressed={readingMode === m.id}
          className={`rounded-md font-semibold transition ${
            size === 'md' ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-[10px]'
          } ${
            readingMode === m.id
              ? 'bg-sky-500 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  )

  const concordanceToggle = (size: 'sm' | 'md' = 'sm') => (
    <button
      onClick={() => setConcordanceEnabled((prev) => !prev)}
      aria-pressed={concordanceEnabled}
      title={
        concordanceEnabled
          ? "Strong's Concordance is active — click to turn off inline term highlights and tooltips"
          : "Strong's Concordance is off — click to enable inline term highlights and formal definitions"
      }
      className={`flex items-center gap-1.5 rounded-lg border font-semibold transition shadow-sm ${
        size === 'md' ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-[10px]'
      } ${
        concordanceEnabled
          ? 'border-sky-500/40 bg-sky-950/40 text-sky-200 hover:bg-sky-500/30 hover:text-white'
          : 'border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:border-slate-600'
      }`}
    >
      <span>🏷️ Concordance:</span>
      <span
        className={`font-mono text-[9px] uppercase px-1 rounded ${
          concordanceEnabled
            ? 'bg-sky-500/30 text-sky-200 font-bold'
            : 'bg-black/30 text-slate-500'
        }`}
      >
        {concordanceEnabled ? 'ON' : 'OFF'}
      </span>
    </button>
  )

  const overviewQuery = allQuestionsSearch.trim().toLowerCase()
  const filteredAllDrills = overviewQuery
    ? allDrills.filter(
        (d) =>
          d.title.toLowerCase().includes(overviewQuery) ||
          d.category.toLowerCase().includes(overviewQuery) ||
          d.tags.some((tag) => tag.toLowerCase().includes(overviewQuery))
      )
    : allDrills
  const overviewGroups = TRACKS.map((t) => ({
    track: t,
    items: filteredAllDrills.filter((d) => d.track === t.id),
  })).filter((g) => g.items.length > 0)

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />

      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-line pb-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="text-2xl">🛠</span>
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Pre-LeetCode Fundamentals Studio
            </h1>
            <span className="chip border-sky-500/40 bg-sky-950/40 text-sky-300 text-[11px] font-semibold">
              🏛️ Grounded in MIT 6.0001: Intro to CS & Python (Grimson, Guttag, Bell)
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Follow the 3-step learning loop: <strong>1. MIT 6.0001 Lecture & Companion Text</strong> ➔ <strong>2. Finger Exercise / Pset Scaffold</strong> ➔ <strong>3. Socratic AI Guide</strong>.
          </p>
        </div>

        {/* Speed-Run Timer Widget */}
        <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-950/20 px-3 py-1.5">
          <div className="text-right font-mono">
            <p className="text-[10px] text-amber-400 font-bold uppercase">Reflex Target</p>
            <p
              className={`text-base font-bold ${
                timerSec <= 10 ? 'text-rose-400 animate-ping' : 'text-amber-300'
              }`}
            >
              {timerSec}s
            </p>
          </div>
          <button
            onClick={() => setTimerRunning((r) => !r)}
            className="btn btn-secondary px-2 py-1 text-xs"
          >
            {timerRunning ? '⏸ Pause' : '⏱ Start'}
          </button>
        </div>
      </div>

      {/* Track Selector Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {TRACKS.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTrack(t.id)}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                activeTrack === t.id
                  ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20'
                  : 'bg-ink-soft text-slate-400 hover:text-slate-200 hover:bg-ink-soft/80'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowAllQuestions(true)}
          className="flex flex-shrink-0 items-center gap-2 rounded-xl border border-sky-500/40 bg-sky-950/30 px-3 py-1.5 text-xs font-bold text-sky-200 hover:bg-sky-500/20 hover:text-white transition shadow"
          title="See every question across every chapter"
        >
          <span>📋 All Questions</span>
          {allDrills.length > 0 && (
            <span className="chip border-sky-400/60 bg-sky-500/10 text-[10px] text-sky-300">
              {allDrills.filter((d) => d.last_status === 'Accepted').length}/{allDrills.length}
            </span>
          )}
        </button>
      </div>

      {/* Drills List Strip */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {drills.map((d, idx) => (
          <button
            key={d.slug}
            onClick={() => setSelectedDrillSlug(d.slug)}
            className={`flex-shrink-0 flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              selectedDrillSlug === d.slug
                ? 'border-sky-500 bg-sky-500/15 text-sky-200 shadow'
                : 'border-ink-line bg-[#0d1117] text-slate-400 hover:text-slate-200'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                d.last_status === 'Accepted'
                  ? 'bg-emerald-400'
                  : d.has_submission
                  ? 'bg-amber-400'
                  : 'bg-slate-600'
              }`}
            />
            <span>
              {idx + 1}. {d.title}
            </span>
          </button>
        ))}
      </div>

      {/* Main Split-Pane Workbench */}
      {drillDetail && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left Column: 3-Step Guided Workflow */}
          <div className="flex flex-col rounded-xl border border-ink-line bg-[#0d1117] overflow-hidden shadow-2xl">
            {/* Step Navigation Tabs */}
            <div className="flex items-center justify-between border-b border-ink-line/80 bg-[#161b22] px-3 py-2 text-xs">
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setActiveTab('textbook')}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 font-medium transition ${
                    activeTab === 'textbook'
                      ? 'bg-sky-500/20 text-sky-200 font-bold border border-sky-500/40 shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>📖 1. MIT 6.0001 Lesson</span>
                </button>

                <button
                  onClick={() => setActiveTab('question')}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 font-medium transition ${
                    activeTab === 'question'
                      ? 'bg-sky-500/20 text-sky-200 font-bold border border-sky-500/40 shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>✍️ 2. Question</span>
                </button>

                <button
                  onClick={() => setActiveTab('socratic')}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 font-medium transition ${
                    activeTab === 'socratic'
                      ? 'bg-purple-500/20 text-purple-200 font-bold border border-purple-500/40 shadow'
                      : isFailed
                      ? 'text-amber-300 font-bold animate-pulse bg-amber-500/10 border border-amber-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>🤖 3. Socratic Guide</span>
                  {isFailed && <span className="h-2 w-2 rounded-full bg-rose-400" />}
                </button>
              </div>

              {/* Prev / Next & Fullscreen Controls */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setIsFullscreenReading(true)}
                  className="flex items-center gap-1 rounded-lg border border-sky-500/30 bg-sky-950/40 px-2 py-1 text-[11px] font-semibold text-sky-300 hover:bg-sky-500/20 hover:text-white transition shadow-sm"
                  title="Open Fullscreen Focus Reading Mode (Esc to exit)"
                >
                  <span>⛶ Fullscreen</span>
                </button>

                <div className="flex items-center gap-1 border-l border-ink-line/80 pl-1.5">
                  <button
                    disabled={currentIndex <= 0}
                    onClick={() => setSelectedDrillSlug(drills[currentIndex - 1].slug)}
                    className="btn px-2 py-0.5 text-xs disabled:opacity-40"
                    title="Previous drill"
                  >
                    ◀
                  </button>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {currentIndex + 1}/{drills.length}
                  </span>
                  <button
                    disabled={currentIndex >= drills.length - 1}
                    onClick={() => setSelectedDrillSlug(drills[currentIndex + 1].slug)}
                    className="btn px-2 py-0.5 text-xs disabled:opacity-40"
                    title="Next drill"
                  >
                    ▶
                  </button>
                </div>
              </div>
            </div>

            {/* Step Failure Alert Banner */}
            {isFailed && activeTab !== 'socratic' && (
              <div className="flex items-center justify-between gap-3 bg-amber-950/40 border-b border-amber-500/30 px-4 py-2 text-xs text-amber-200">
                <div className="flex items-center gap-2">
                  <span className="text-base">💡</span>
                  <span>Test cases failed ({runResult?.status}). Need a hint without spoilers?</span>
                </div>
                <button
                  onClick={() => setActiveTab('socratic')}
                  className="rounded-lg bg-amber-500/20 border border-amber-500/40 px-2.5 py-1 text-xs font-bold text-amber-100 hover:bg-amber-500/30 transition"
                >
                  Ask Socratic Guide ➔
                </button>
              </div>
            )}

            {/* Tab Body Content Area */}
            <div className="p-5 text-xs text-slate-300 leading-relaxed overflow-y-auto max-h-[580px] space-y-4">
              {/* TAB 1: 📖 Guttag Textbook Lesson */}
              {activeTab === 'textbook' && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/60 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="chip border-sky-500/40 bg-sky-950/30 text-sky-300 font-semibold">
                        🏛️ MIT 6.0001 (John V. Guttag)
                      </span>
                      <span className="chip border-slate-700 text-slate-400">
                        {drillDetail.category}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {readingModeToggle('sm')}
                      {concordanceToggle('sm')}
                      <button
                        onClick={() => setIsFullscreenReading(true)}
                        className="flex items-center gap-1 rounded-md border border-sky-500/40 bg-sky-950/40 px-2.5 py-1 text-[11px] font-bold text-sky-200 hover:bg-sky-500/30 hover:text-white transition shadow"
                        title="Expand to Fullscreen Focus Reading Mode"
                      >
                        <span>⛶ Fullscreen Mode</span>
                      </button>
                      <span className="text-[11px] font-mono text-slate-400">
                        📖 {lessonReadTime}
                      </span>
                    </div>
                  </div>

                  {renderGuidingQuestionsBox(true)}

                  {drillDetail.editorial ? (
                    <>
                      <ConcordanceReader
                        content={lessonMarkdown}
                        enabled={concordanceEnabled}
                        onToggleEnabled={setConcordanceEnabled}
                      />
                      {lessonSections.shown < lessonSections.total && (
                        <button
                          onClick={() => setReadingMode('robust')}
                          className="w-full rounded-lg border border-dashed border-sky-500/40 bg-sky-950/20 px-4 py-2.5 text-[11px] text-sky-300 hover:bg-sky-500/10 hover:text-sky-200 transition"
                        >
                          Showing {lessonSections.shown} of {lessonSections.total} sections —
                          switch to <strong>Robust</strong> for the textbook reading and pitfalls ➔
                        </button>
                      )}
                    </>
                  ) : (
                    <p className="text-slate-400 italic">No textbook excerpt available.</p>
                  )}

                  {/* Canonical Solution Snippet */}
                  {drillDetail.solutions?.python && (
                    <div className="space-y-1.5 pt-2">
                      <p className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider">
                        MIT 6.0001 Canonical Pattern:
                      </p>
                      <pre className="rounded-lg border border-emerald-500/30 bg-emerald-950/15 p-3.5 text-emerald-300 font-mono overflow-x-auto whitespace-pre text-xs">
                        {drillDetail.solutions.python}
                      </pre>
                    </div>
                  )}

                  <div className="pt-3 flex justify-between items-center border-t border-ink-line/60">
                    <span className="text-[11px] text-slate-400">
                      Mastered the concept? Test your understanding with the exercise.
                    </span>
                    <button
                      onClick={() => setActiveTab('question')}
                      className="btn btn-primary px-4 py-2 text-xs font-bold shadow-lg"
                    >
                      Proceed to Question ➔
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 2: ✍️ Question & Finger Exercise */}
              {activeTab === 'question' && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="chip border-emerald-500/40 text-emerald-300">
                        {drillDetail.difficulty}
                      </span>
                      <span className="chip border-slate-700 text-slate-400">
                        Finger Exercise
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      {drillDetail.solutions && Object.keys(drillDetail.solutions).length > 0 && (
                        <button
                          onClick={() => setShowPeekAnswer((prev) => !prev)}
                          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition border ${
                            showPeekAnswer
                              ? 'border-amber-500/50 bg-amber-950/40 text-amber-200 shadow-sm'
                              : 'border-slate-700 bg-slate-800/60 text-slate-300 hover:border-amber-500/30 hover:text-amber-200'
                          }`}
                          title={showPeekAnswer ? 'Hide answer' : 'Peek canonical answer'}
                        >
                          <span>{showPeekAnswer ? '🙈 Hide Answer' : '👁️ Peek Answer'}</span>
                        </button>
                      )}
                      <button
                        onClick={() => setActiveTab('socratic')}
                        className="text-xs text-sky-400 hover:text-sky-300 underline font-medium"
                      >
                        Need help? Ask Socratic Guide ➔
                      </button>
                    </div>
                  </div>

                  <h2 className="text-base font-bold text-slate-100">{drillDetail.title}</h2>

                  <div className="prose prose-invert text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">
                    {drillDetail.description}
                  </div>

                  {/* Examples */}
                  {drillDetail.examples.length > 0 && (
                    <div className="rounded-lg border border-ink-line/60 bg-[#090d13] p-3 text-xs space-y-1.5">
                      <p className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider">
                        Example:
                      </p>
                      <p className="font-mono text-slate-300">
                        <strong>Input:</strong> {drillDetail.examples[0].input}
                      </p>
                      <p className="font-mono text-emerald-300">
                        <strong>Output:</strong> {drillDetail.examples[0].output}
                      </p>
                      {drillDetail.examples[0].explanation && (
                        <p className="text-slate-400 text-[11px]">
                          {drillDetail.examples[0].explanation}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Constraints */}
                  {drillDetail.constraints.length > 0 && (
                    <div className="rounded-lg border border-ink-line/40 bg-[#090d13] p-3 text-xs space-y-1">
                      <p className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider">
                        Constraints:
                      </p>
                      <ul className="list-disc list-inside space-y-0.5 font-mono text-[11px] text-slate-400">
                        {drillDetail.constraints.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Hints */}
                  {drillDetail.hints.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <p className="font-bold text-slate-400 text-xs uppercase tracking-wider">
                        Hints
                      </p>
                      {drillDetail.hints.map((hint, i) => (
                        <details
                          key={i}
                          className="rounded-lg border border-ink-line/60 bg-[#090d13] p-2.5 text-xs"
                        >
                          <summary className="font-medium text-slate-300 cursor-pointer select-none">
                            Hint {i + 1}
                          </summary>
                          <p className="mt-1.5 text-slate-400 text-[11px]">{hint}</p>
                        </details>
                      ))}
                    </div>
                  )}

                  {/* Peek Answer / Canonical Solution Section */}
                  {drillDetail.solutions && Object.keys(drillDetail.solutions).length > 0 && (
                    <div className="space-y-2 pt-2">
                      <div className="flex items-center justify-between border-t border-ink-line/40 pt-3">
                        <div>
                          <p className="font-bold text-slate-400 text-xs uppercase tracking-wider">
                            Answer / Solution
                          </p>
                          <p className="text-[11px] text-slate-500">
                            Stuck or want to check your approach against the textbook?
                          </p>
                        </div>
                        <button
                          onClick={() => setShowPeekAnswer((prev) => !prev)}
                          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition border ${
                            showPeekAnswer
                              ? 'border-amber-500/50 bg-amber-950/40 text-amber-200 shadow-sm'
                              : 'border-slate-700 bg-slate-800/60 text-slate-300 hover:border-amber-500/30 hover:text-amber-200'
                          }`}
                        >
                          <span>{showPeekAnswer ? '🙈 Hide Answer' : '👁️ Peek Answer'}</span>
                        </button>
                      </div>

                      {showPeekAnswer && (
                        <div className="rounded-xl border border-amber-500/40 bg-[#090d14] p-4 space-y-3 shadow-xl animate-in fade-in duration-150">
                          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/60 pb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-base">💡</span>
                              <span className="font-bold text-amber-300 text-xs uppercase tracking-wider">
                                Canonical Solution (MIT 6.0001 Pattern)
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => {
                                  const sol =
                                    drillDetail.solutions?.python ||
                                    Object.values(drillDetail.solutions || {})[0] ||
                                    ''
                                  if (sol) void navigator.clipboard.writeText(sol)
                                }}
                                className="flex items-center gap-1 rounded bg-slate-800 px-2 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                                title="Copy solution to clipboard"
                              >
                                📋 Copy
                              </button>
                              <button
                                onClick={() => {
                                  const sol =
                                    drillDetail.solutions?.python ||
                                    Object.values(drillDetail.solutions || {})[0] ||
                                    ''
                                  if (sol) setCode(sol)
                                }}
                                className="flex items-center gap-1 rounded bg-sky-500/20 border border-sky-500/40 px-2.5 py-1 text-[11px] font-bold text-sky-200 hover:bg-sky-500/30 hover:text-white transition"
                                title="Load this solution into code editor"
                              >
                                Load into Editor ➔
                              </button>
                            </div>
                          </div>

                          <pre className="rounded-lg border border-emerald-500/30 bg-[#05080e] p-3.5 text-emerald-300 font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed shadow-inner">
                            {drillDetail.solutions.python || Object.values(drillDetail.solutions)[0]}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Export to Deck */}
                  {decks.length > 0 && (
                    <div className="border-t border-ink-line/60 pt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="text-slate-400">Add to Spaced Repetition deck:</span>
                      <select
                        onChange={(e) => {
                          if (e.target.value) handleExportCard(e.target.value)
                        }}
                        defaultValue=""
                        className="rounded border border-ink-line bg-[#090d13] px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
                      >
                        <option value="" disabled>
                          Select deck…
                        </option>
                        {decks.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  {exportMsg && <p className="text-xs text-emerald-400 font-semibold">{exportMsg}</p>}
                </div>
              )}

              {/* TAB 3: 🤖 Socratic Guide */}
              {activeTab === 'socratic' && (
                <CodeSocraticTutor
                  problemTitle={drillDetail.title}
                  problemSlug={drillDetail.slug}
                  code={code}
                  language="python"
                />
              )}
            </div>
          </div>

          {/* Right Column: Code Editor & Test Console */}
          <div className="space-y-4">
            <CodeEditor
              code={code}
              onChange={setCode}
              language="python"
              height="280px"
              onRun={handleRun}
              onSubmit={handleSubmit}
              onReset={() => {
                const starter =
                  drillDetail.starter_codes?.python || drillDetail.starter_codes?.typescript || ''
                setCode(starter)
              }}
            />

            <CodeTestConsole
              testCases={drillDetail.test_cases}
              runResult={runResult}
              running={running}
              onRun={handleRun}
              onSubmit={handleSubmit}
              submitting={submitting}
            />
          </div>
        </div>
      )}

      {/* ALL QUESTIONS OVERVIEW MODAL */}
      {showAllQuestions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[88vh] flex flex-col rounded-2xl border border-sky-500/40 bg-[#0d131f] shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-sky-500/30 bg-[#121927] px-6 py-4">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">📋</span>
                <div>
                  <h3 className="text-base font-bold text-slate-100">All Questions, Every Chapter</h3>
                  <p className="text-[11px] text-slate-400">
                    {allDrills.filter((d) => d.last_status === 'Accepted').length} of {allDrills.length}{' '}
                    solved across {TRACKS.length} chapters
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowAllQuestions(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
              >
                ✕
              </button>
            </div>

            <div className="p-4 border-b border-ink-line/60 bg-[#090d14]">
              <input
                type="text"
                value={allQuestionsSearch}
                onChange={(e) => setAllQuestionsSearch(e.target.value)}
                placeholder="Search by title, category or tag…"
                className="w-full rounded-xl border border-sky-500/30 bg-[#0d131f] px-4 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-400"
                autoFocus
              />
            </div>

            <div className="p-5 overflow-y-auto space-y-5 text-xs">
              {overviewGroups.length === 0 && (
                <p className="text-center py-8 text-slate-500">
                  No questions match “{allQuestionsSearch}”.
                </p>
              )}

              {overviewGroups.map(({ track, items }) => (
                <div key={track.id} className="space-y-2">
                  <h4 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    <span>{track.label}</span>
                    <span className="text-slate-600 font-normal normal-case">
                      ({items.filter((d) => d.last_status === 'Accepted').length}/{items.length})
                    </span>
                  </h4>
                  <div className="space-y-1.5">
                    {items.map((d, idx) => (
                      <button
                        key={d.slug}
                        onClick={() => openDrillFromOverview(d)}
                        className={`w-full flex items-center gap-3 rounded-lg border px-3 py-2 text-left transition ${
                          d.slug === selectedDrillSlug && d.track === activeTrack
                            ? 'border-sky-500 bg-sky-500/10'
                            : 'border-ink-line/60 bg-[#080d14] hover:border-sky-500/40 hover:bg-sky-950/20'
                        }`}
                      >
                        <span
                          className={`h-2 w-2 flex-shrink-0 rounded-full ${
                            d.last_status === 'Accepted'
                              ? 'bg-emerald-400'
                              : d.has_submission
                              ? 'bg-amber-400'
                              : 'bg-slate-600'
                          }`}
                        />
                        <span className="text-slate-500 font-mono text-[11px] w-5 flex-shrink-0">
                          {idx + 1}.
                        </span>
                        <span className="flex-1 text-slate-200 font-medium">{d.title}</span>
                        <span className="chip border-slate-700 text-slate-400 text-[10px] flex-shrink-0">
                          {d.difficulty}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* FULLSCREEN FOCUS READING OVERLAY */}
      {isFullscreenReading && drillDetail && (
        <div className="fixed inset-0 z-50 flex flex-col bg-[#080c14] text-slate-100 backdrop-blur-lg animate-in fade-in duration-150">
          {/* Top Fullscreen Control Bar */}
          <div className="flex flex-wrap items-center justify-between border-b border-sky-500/30 bg-[#0d131f] px-6 py-3 shadow-lg">
            <div className="flex items-center gap-3">
              <span className="chip border-sky-400 bg-sky-950 text-sky-300 font-semibold text-xs">
                🏛️ MIT 6.0001 Focus Mode
              </span>
              <div>
                <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <span>{drillDetail.title}</span>
                  <span className="text-xs text-slate-400 font-normal">({drillDetail.category})</span>
                </h2>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {readingModeToggle('md')}
              {concordanceToggle('md')}

              {/* Prev / Next Controls */}
              <div className="flex items-center gap-1 bg-[#161f2e] border border-ink-line/80 rounded-lg p-1">
                <button
                  disabled={currentIndex <= 0}
                  onClick={() => setSelectedDrillSlug(drills[currentIndex - 1].slug)}
                  className="btn px-2 py-0.5 text-xs disabled:opacity-40"
                  title="Previous drill"
                >
                  ◀
                </button>
                <span className="text-xs text-slate-400 font-mono px-2">
                  {currentIndex + 1} / {drills.length}
                </span>
                <button
                  disabled={currentIndex >= drills.length - 1}
                  onClick={() => setSelectedDrillSlug(drills[currentIndex + 1].slug)}
                  className="btn px-2 py-0.5 text-xs disabled:opacity-40"
                  title="Next drill"
                >
                  ▶
                </button>
              </div>

              <button
                onClick={() => {
                  setIsFullscreenReading(false)
                  setActiveTab('question')
                }}
                className="btn btn-primary px-3.5 py-1.5 text-xs font-bold shadow"
              >
                Proceed to Question ➔
              </button>

              <button
                onClick={() => setIsFullscreenReading(false)}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-bold text-slate-300 hover:bg-slate-700 hover:text-white transition"
                title="Exit Fullscreen (Esc)"
              >
                <span>✕ Exit Fullscreen</span>
                <kbd className="text-[10px] font-mono bg-black/40 px-1.5 py-0.5 rounded text-slate-400">Esc</kbd>
              </button>
            </div>
          </div>

          {/* Fullscreen Reading Container */}
          <div className="flex-1 overflow-y-auto px-6 py-8">
            <div className="max-w-4xl mx-auto space-y-6">
              {renderGuidingQuestionsBox(false)}

              {drillDetail.editorial ? (
                <>
                  <ConcordanceReader
                    content={lessonMarkdown}
                    enabled={concordanceEnabled}
                    onToggleEnabled={setConcordanceEnabled}
                  />
                  {lessonSections.shown < lessonSections.total && (
                    <button
                      onClick={() => setReadingMode('robust')}
                      className="w-full rounded-xl border border-dashed border-sky-500/40 bg-sky-950/20 px-4 py-3 text-xs text-sky-300 hover:bg-sky-500/10 hover:text-sky-200 transition"
                    >
                      Showing {lessonSections.shown} of {lessonSections.total} sections —
                      switch to <strong>Robust</strong> for the textbook reading and pitfalls ➔
                    </button>
                  )}
                </>
              ) : (
                <p className="text-slate-400 italic">No textbook excerpt available.</p>
              )}

              {/* Canonical Solution Snippet */}
              {drillDetail.solutions?.python && (
                <div className="space-y-2 pt-4 border-t border-ink-line/60">
                  <p className="font-semibold text-slate-400 uppercase text-xs tracking-wider">
                    MIT 6.0001 Canonical Pattern:
                  </p>
                  <pre className="rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-5 text-emerald-300 font-mono overflow-x-auto whitespace-pre text-sm shadow-inner">
                    {drillDetail.solutions.python}
                  </pre>
                </div>
              )}

              <div className="pt-6 pb-12 flex justify-between items-center border-t border-ink-line/60">
                <span className="text-xs text-slate-400">
                  Ready to apply the concept? Transition to the interactive coding exercise.
                </span>
                <button
                  onClick={() => {
                    setIsFullscreenReading(false)
                    setActiveTab('question')
                  }}
                  className="btn btn-primary px-6 py-2.5 text-sm font-bold shadow-xl"
                >
                  Proceed to Question ➔
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
