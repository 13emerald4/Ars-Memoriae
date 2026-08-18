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
import { CodeTestConsole } from '../components/CodeTestConsole'
import { ErrorNote, Spinner } from '../components/ui'

const TRACKS = [
  { id: 'track_0_python_basics', label: '🟢 Track 0: Python Basics & Numerics (Guttag Ch. 2–3)', icon: '🐍' },
  { id: 'track_1_pythonic_fluency', label: '🔵 Track 1: Structured Types & Aliasing (Guttag Ch. 4–5)', icon: '⚡' },
  { id: 'track_2_data_structures', label: '🟣 Track 2: Abstract Data Types & Queues (Guttag Ch. 10)', icon: '🧱' },
  { id: 'track_3_algorithmic_scaffolds', label: '🟡 Track 3: Recursion & Scaffolds (Guttag Ch. 6, 12, 15)', icon: '📐' },
  { id: 'track_4_custom_sorting', label: '🟠 Track 4: Divide-and-Conquer Sorting (Guttag Ch. 12)', icon: '🔀' },
  { id: 'track_5_bit_manipulation', label: '🔴 Track 5: Binary Encodings & Bits (Guttag Ch. 3.4)', icon: '🔢' },
  { id: 'track_6_complexity_math', label: '🟤 Track 6: Asymptotic Complexity & Math (Guttag Ch. 11)', icon: '⏱' },
]

export default function FundamentalsStudio() {
  const [activeTrack, setActiveTrack] = useState<string>('track_0_python_basics')
  const [drills, setDrills] = useState<CodeProblemSummary[]>([])
  const [selectedDrillSlug, setSelectedDrillSlug] = useState<string | null>(null)
  const [drillDetail, setDrillDetail] = useState<CodeProblemOut | null>(null)
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

  const loadDrills = useCallback(async () => {
    try {
      setLoading(true)
      const list = await api.listCodeProblems({ kind: 'fundamental', track: activeTrack })
      setDrills(list)
      if (list.length > 0) {
        setSelectedDrillSlug(list[0].slug)
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
              🏛️ Grounded in MIT 6.0001 (John V. Guttag)
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Build computational fluency and reflex automaticity across Guttag's foundational Python concepts, data structures, and algorithmic scaffolds before tackling LeetCode.
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
          {/* Left Column: Drill Description & Rule */}
          <div className="space-y-4 rounded-xl border border-ink-line bg-[#0d1117] p-5 shadow-xl">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/60 pb-3">
              <div className="flex items-center gap-2">
                <span className="chip border-emerald-500/40 text-emerald-300">
                  {drillDetail.difficulty}
                </span>
                <span className="chip border-slate-700 text-slate-400">
                  {drillDetail.category}
                </span>
              </div>

              {/* Navigation Controls */}
              <div className="flex items-center gap-1.5">
                <button
                  disabled={currentIndex <= 0}
                  onClick={() => setSelectedDrillSlug(drills[currentIndex - 1].slug)}
                  className="btn px-2 py-1 text-xs disabled:opacity-40"
                >
                  ◀ Prev
                </button>
                <span className="text-xs text-slate-500 font-mono">
                  {currentIndex + 1} / {drills.length}
                </span>
                <button
                  disabled={currentIndex >= drills.length - 1}
                  onClick={() => setSelectedDrillSlug(drills[currentIndex + 1].slug)}
                  className="btn px-2 py-1 text-xs disabled:opacity-40"
                >
                  Next ▶
                </button>
              </div>
            </div>

            <h2 className="text-lg font-bold text-slate-100">{drillDetail.title}</h2>

            <div className="prose prose-invert text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">
              {drillDetail.description}
            </div>

            {/* Example Block */}
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
                  <p className="text-slate-500 text-[11px]">
                    {drillDetail.examples[0].explanation}
                  </p>
                )}
              </div>
            )}

            {/* Rule / Key Intuition */}
            {drillDetail.editorial && (
              <details className="rounded-lg border border-sky-500/30 bg-sky-950/20 p-3 text-xs">
                <summary className="font-bold text-sky-300 cursor-pointer select-none">
                  💡 Key Rule & Pattern Intuition
                </summary>
                <div className="mt-2 text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {drillDetail.editorial}
                </div>
              </details>
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
    </div>
  )
}
