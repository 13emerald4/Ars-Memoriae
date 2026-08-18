import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type {
  CodeProblemOut,
  CodeProblemSummary,
  CodeSubmissionOut,
  Deck,
  RunCodeResponse,
  SubmitCodeResponse,
} from '../api/types'
import { CodeEditor } from '../components/CodeEditor'
import { CodeSocraticTutor } from '../components/CodeSocraticTutor'
import { CodeTestConsole } from '../components/CodeTestConsole'
import { ErrorNote, Modal, Spinner } from '../components/ui'

export default function CodeLab() {
  const [problems, setProblems] = useState<CodeProblemSummary[]>([])
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [problemDetail, setProblemDetail] = useState<CodeProblemOut | null>(null)
  const [activeTab, setActiveTab] = useState<
    'description' | 'editorial' | 'solutions' | 'submissions' | 'tutor'
  >('description')

  const [language, setLanguage] = useState<string>('python')
  const [code, setCode] = useState<string>('')
  const [submissions, setSubmissions] = useState<CodeSubmissionOut[]>([])
  const [decks, setDecks] = useState<Deck[]>([])

  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [runResult, setRunResult] = useState<RunCodeResponse | SubmitCodeResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [exportMsg, setExportMsg] = useState<string | null>(null)

  // AI Forge Modal State
  const [forgeOpen, setForgeOpen] = useState(false)
  const [forgeTopic, setForgeTopic] = useState('')
  const [forgeDifficulty, setForgeDifficulty] = useState('Medium')
  const [forging, setForging] = useState(false)

  // Timer
  const [timerSec, setTimerSec] = useState(0)
  const [timerActive, setTimerActive] = useState(false)

  const loadProblems = useCallback(async () => {
    try {
      setLoading(true)
      const list = await api.listCodeProblems({ kind: 'problem' })
      setProblems(list)
      if (list.length > 0 && !selectedSlug) {
        setSelectedSlug(list[0].slug)
      }
      const dList = await api.decks()
      setDecks(dList)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [selectedSlug])

  useEffect(() => {
    void loadProblems()
  }, [loadProblems])

  // Load problem details
  useEffect(() => {
    if (!selectedSlug) return
    let active = true
    api
      .getCodeProblem(selectedSlug)
      .then((detail) => {
        if (!active) return
        setProblemDetail(detail)
        const starter =
          detail.starter_codes?.[language] ||
          detail.starter_codes?.python ||
          detail.starter_codes?.typescript ||
          ''
        setCode(starter)
        setRunResult(null)
        setTimerSec(0)
        setTimerActive(true)
      })
      .catch((err) => {
        if (active) setError(err)
      })

    api
      .listCodeSubmissions(undefined, 10)
      .then((subs) => {
        if (active) setSubmissions(subs)
      })
      .catch(() => {})

    return () => {
      active = false
    }
  }, [selectedSlug, language])

  // Timer tick
  useEffect(() => {
    let interval: any
    if (timerActive) {
      interval = setInterval(() => setTimerSec((s) => s + 1), 1000)
    }
    return () => clearInterval(interval)
  }, [timerActive])

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60)
    const secs = totalSec % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const handleRun = async () => {
    if (!problemDetail) return
    setRunning(true)
    setError(null)
    try {
      const res = await api.runCode(problemDetail.slug, {
        code,
        language,
      })
      setRunResult(res)
    } catch (err) {
      setError(err)
    } finally {
      setRunning(false)
    }
  }

  const handleSubmit = async () => {
    if (!problemDetail) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await api.submitCode(problemDetail.slug, {
        code,
        language,
      })
      setRunResult(res)
      const subs = await api.listCodeSubmissions(undefined, 10)
      setSubmissions(subs)
      void loadProblems()
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const handleForge = async () => {
    if (!forgeTopic.trim()) return
    setForging(true)
    setError(null)
    try {
      const newProb = await api.forgeProblem({
        topic: forgeTopic.trim(),
        difficulty: forgeDifficulty,
        target_language: language,
      })
      setForgeOpen(false)
      setForgeTopic('')
      await loadProblems()
      setSelectedSlug(newProb.slug)
    } catch (err) {
      setError(err)
    } finally {
      setForging(false)
    }
  }

  const handleExportCard = async (deckId: string) => {
    if (!problemDetail) return
    try {
      const resp = await api.exportProblemToCard(problemDetail.slug, deckId)
      setExportMsg(resp.message)
      setTimeout(() => setExportMsg(null), 4000)
    } catch (err) {
      setError(err)
    }
  }

  if (loading && problems.length === 0) return <Spinner />

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />

      {/* Top Action & Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-line pb-4">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedSlug || ''}
            onChange={(e) => setSelectedSlug(e.target.value)}
            className="rounded-xl border border-ink-line bg-[#0d1117] px-3.5 py-2 text-sm font-semibold text-slate-100 focus:border-sky-500 focus:outline-none max-w-[340px]"
          >
            {problems.map((p) => (
              <option key={p.slug} value={p.slug}>
                {p.difficulty === 'Easy' ? '🟢' : p.difficulty === 'Medium' ? '🟡' : '🔴'} {p.title}
              </option>
            ))}
          </select>

          <button
            onClick={() => setForgeOpen(true)}
            className="btn btn-secondary px-3 py-1.5 text-xs font-semibold"
          >
            ✨ Forge with AI
          </button>
        </div>

        {/* Timer & Export */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-xl border border-ink-line/80 bg-[#0d1117] px-3 py-1 text-xs font-mono text-slate-300">
            <span>⏱</span>
            <span className="font-bold text-amber-300">{formatTimer(timerSec)}</span>
            <button
              onClick={() => setTimerActive((a) => !a)}
              className="text-[10px] text-slate-500 hover:text-slate-300"
            >
              {timerActive ? '⏸' : '▶'}
            </button>
          </div>

          {decks.length > 0 && problemDetail && (
            <select
              onChange={(e) => {
                if (e.target.value) handleExportCard(e.target.value)
              }}
              defaultValue=""
              className="rounded-lg border border-ink-line/80 bg-[#0d1117] px-2.5 py-1 text-xs text-slate-300 focus:outline-none"
            >
              <option value="" disabled>
                ➕ Add to Deck…
              </option>
              {decks.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
      {exportMsg && <p className="text-xs text-emerald-400 font-semibold">{exportMsg}</p>}

      {/* Main Split-Pane Workbench */}
      {problemDetail && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left Pane (Description, Editorial, Solutions, Submissions, AI Tutor) */}
          <div className="flex flex-col rounded-xl border border-ink-line bg-[#0d1117] overflow-hidden shadow-2xl">
            {/* Tab Bar */}
            <div className="flex flex-wrap items-center gap-1 border-b border-ink-line/80 bg-[#161b22] px-3 py-2 text-xs">
              {(
                [
                  ['description', '📋 Description'],
                  ['editorial', '💡 Editorial & Learn'],
                  ['solutions', '✨ Solutions'],
                  ['submissions', '📊 Submissions'],
                  ['tutor', '🤖 Socratic AI'],
                ] as const
              ).map(([tabId, label]) => (
                <button
                  key={tabId}
                  onClick={() => setActiveTab(tabId)}
                  className={`rounded-lg px-2.5 py-1 font-medium transition ${
                    activeTab === tabId
                      ? 'bg-ink text-sky-300 font-semibold shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Tab Body Content */}
            <div className="p-5 text-xs text-slate-300 leading-relaxed overflow-y-auto max-h-[640px] space-y-4">
              {activeTab === 'description' && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`chip ${
                        problemDetail.difficulty === 'Easy'
                          ? 'border-emerald-500/40 text-emerald-300'
                          : problemDetail.difficulty === 'Medium'
                          ? 'border-amber-500/40 text-amber-300'
                          : 'border-rose-500/40 text-rose-300'
                      }`}
                    >
                      {problemDetail.difficulty}
                    </span>
                    <span className="chip border-slate-700 text-slate-400">
                      {problemDetail.category}
                    </span>
                    {problemDetail.tags.map((tag) => (
                      <span key={tag} className="chip border-ink-line text-slate-500">
                        {tag}
                      </span>
                    ))}
                  </div>

                  <h2 className="text-base font-bold text-slate-100">{problemDetail.title}</h2>

                  <div className="prose prose-invert text-xs whitespace-pre-wrap leading-relaxed">
                    {problemDetail.description}
                  </div>

                  {/* Examples */}
                  {problemDetail.examples.map((ex, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-ink-line/60 bg-[#090d13] p-3 text-xs space-y-1.5"
                    >
                      <p className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider">
                        Example {idx + 1}:
                      </p>
                      <p className="font-mono text-slate-200">
                        <strong>Input:</strong> {ex.input}
                      </p>
                      <p className="font-mono text-emerald-300">
                        <strong>Output:</strong> {ex.output}
                      </p>
                      {ex.explanation && (
                        <p className="text-slate-400 text-[11px] whitespace-pre-wrap">
                          {ex.explanation}
                        </p>
                      )}
                    </div>
                  ))}

                  {/* Constraints */}
                  {problemDetail.constraints.length > 0 && (
                    <div className="rounded-lg border border-ink-line/40 bg-[#090d13] p-3 text-xs space-y-1">
                      <p className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider">
                        Constraints:
                      </p>
                      <ul className="list-disc list-inside space-y-0.5 font-mono text-[11px] text-slate-400">
                        {problemDetail.constraints.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Hints */}
                  {problemDetail.hints.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <p className="font-bold text-slate-400 text-xs uppercase tracking-wider">
                        Hints
                      </p>
                      {problemDetail.hints.map((hint, i) => (
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
                </div>
              )}

              {activeTab === 'editorial' && (
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-sky-300">
                    💡 Pattern Intuition & Mathematical Proof
                  </h3>
                  {problemDetail.editorial ? (
                    <div className="prose prose-invert text-xs whitespace-pre-wrap leading-relaxed text-slate-200">
                      {problemDetail.editorial}
                    </div>
                  ) : (
                    <p className="text-slate-500 italic">No editorial written yet.</p>
                  )}
                </div>
              )}

              {activeTab === 'solutions' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-emerald-300">
                    ✨ Canonical Reference Solutions
                  </h3>
                  {Object.entries(problemDetail.solutions).map(([lang, solCode]) => (
                    <div key={lang} className="space-y-1">
                      <p className="font-bold text-xs uppercase text-slate-400">{lang}</p>
                      <pre className="rounded-lg border border-ink-line/60 bg-[#090d13] p-3 text-xs text-emerald-300 font-mono overflow-x-auto whitespace-pre">
                        {solCode}
                      </pre>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'submissions' && (
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-slate-100">📊 Past Submissions</h3>
                  {submissions.length === 0 ? (
                    <p className="text-slate-500 italic">No submissions recorded yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {submissions.map((sub) => (
                        <div
                          key={sub.id}
                          className="flex items-center justify-between rounded-lg border border-ink-line/60 bg-[#090d13] p-2.5 text-xs font-mono"
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className={`font-bold ${
                                sub.status === 'Accepted' ? 'text-emerald-400' : 'text-rose-400'
                              }`}
                            >
                              {sub.status}
                            </span>
                            <span className="text-slate-500">
                              ({sub.passed_tests}/{sub.total_tests})
                            </span>
                          </div>
                          <div className="text-slate-400 text-[11px]">
                            {sub.runtime_ms ? `${sub.runtime_ms} ms` : ''} •{' '}
                            {new Date(sub.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'tutor' && (
                <CodeSocraticTutor
                  problemTitle={problemDetail.title}
                  problemSlug={problemDetail.slug}
                  code={code}
                  language={language}
                />
              )}
            </div>
          </div>

          {/* Right Pane (Code Editor & Test Console) */}
          <div className="space-y-4">
            <CodeEditor
              code={code}
              onChange={setCode}
              language={language}
              onLanguageChange={setLanguage}
              height="360px"
              onRun={handleRun}
              onSubmit={handleSubmit}
              onReset={() => {
                const starter =
                  problemDetail.starter_codes?.[language] ||
                  problemDetail.starter_codes?.python ||
                  problemDetail.starter_codes?.typescript ||
                  ''
                setCode(starter)
              }}
            />

            <CodeTestConsole
              testCases={problemDetail.test_cases}
              runResult={runResult}
              running={running}
              onRun={handleRun}
              onSubmit={handleSubmit}
              submitting={submitting}
            />
          </div>
        </div>
      )}

      {/* AI Forge Problem Modal */}
      {forgeOpen && (
        <Modal title="✨ Forge New Code Challenge with AI" onClose={() => setForgeOpen(false)}>
          <div className="space-y-4 text-xs">
            <p className="text-slate-400">
              Generate an original, structured algorithmic challenge on any topic with Gemini.
            </p>

            <div>
              <label className="label">Topic / Concept / Algorithm</label>
              <input
                type="text"
                className="input text-xs"
                placeholder="e.g. Monotonic Stack, LRU Cache, Trie Prefix Search, 2D Grid DP"
                value={forgeTopic}
                onChange={(e) => setForgeTopic(e.target.value)}
              />
            </div>

            <div>
              <label className="label">Difficulty</label>
              <select
                className="input text-xs"
                value={forgeDifficulty}
                onChange={(e) => setForgeDifficulty(e.target.value)}
              >
                <option value="Easy">Easy (Fundamentals & Direct Logic)</option>
                <option value="Medium">Medium (Algorithmic Pattern & Optimization)</option>
                <option value="Hard">Hard (Complex DP, Graph & Data Structures)</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                className="btn btn-secondary text-xs"
                onClick={() => setForgeOpen(false)}
                disabled={forging}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary text-xs font-bold"
                onClick={handleForge}
                disabled={forging || !forgeTopic.trim()}
              >
                {forging ? 'Forging Problem…' : 'Generate Challenge'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
