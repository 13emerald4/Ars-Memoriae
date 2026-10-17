import { useState } from 'react'
import type { RunCodeResponse, StudentTestResult, SubmitCodeResponse, TestCaseResult } from '../api/types'

export interface CodeTestConsoleProps {
  testCases: Array<{ input: any; expected: any }>
  runResult: RunCodeResponse | SubmitCodeResponse | null
  running: boolean
  onRun: (customCases?: Array<{ input: any; expected: any }>) => void
  onSubmit: () => void
  submitting: boolean
}

export function CodeTestConsole({
  testCases,
  runResult,
  running,
  onRun,
  onSubmit,
  submitting,
}: CodeTestConsoleProps) {
  const [activeTab, setActiveTab] = useState<'cases' | 'result'>('cases')
  const [selectedCaseIdx, setSelectedCaseIdx] = useState(0)

  // Switch to result tab automatically when run completes
  const handleRunClick = () => {
    setActiveTab('result')
    onRun()
  }

  const handleCaseSelect = (idx: number) => {
    setSelectedCaseIdx(idx)
  }

  const currentCase = testCases[selectedCaseIdx] || testCases[0]
  const currentResult: TestCaseResult | undefined = runResult?.results?.[selectedCaseIdx]

  return (
    <div className="flex flex-col rounded-xl border border-[#282828] bg-[#1a1a1a] text-[#eff1f6] overflow-hidden shadow-2xl">
      {/* Console Tab Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#282828] bg-[#262626] px-4 py-2 text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('cases')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 font-medium transition ${
              activeTab === 'cases'
                ? 'bg-[#1e1e1e] text-[#eff1f6] font-semibold shadow'
                : 'text-[#8a8a8a] hover:text-[#eff1f6]'
            }`}
          >
            <span>🧪 Testcases</span>
          </button>

          <button
            onClick={() => setActiveTab('result')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 font-medium transition ${
              activeTab === 'result'
                ? 'bg-[#1e1e1e] text-[#eff1f6] font-semibold shadow'
                : 'text-[#8a8a8a] hover:text-[#eff1f6]'
            }`}
          >
            <span>📊 Results</span>
            {runResult && (
              <span
                className={`h-2 w-2 rounded-full ${
                  runResult.status === 'Accepted' ? 'bg-[#2cbb5d]' : 'bg-[#ff375f] animate-pulse'
                }`}
              />
            )}
          </button>
        </div>

        {/* Action Run & Submit Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleRunClick}
            disabled={running || submitting}
            className="btn btn-secondary px-3 py-1.5 text-xs font-semibold"
          >
            {running ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-full border-2 border-slate-300 border-t-transparent animate-spin" />
                Running…
              </span>
            ) : (
              '▶ Run'
            )}
          </button>

          <button
            onClick={onSubmit}
            disabled={running || submitting}
            className="btn btn-primary px-4 py-1.5 text-xs font-bold shadow-lg"
          >
            {submitting ? 'Submitting…' : '⚡ Submit'}
          </button>
        </div>
      </div>

      {/* Console Content Area */}
      <div className="p-4 text-xs font-mono min-h-[160px] max-h-[260px] overflow-y-auto">
        {activeTab === 'cases' && (
          <div className="space-y-4">
            {/* Case Buttons */}
            <div className="flex flex-wrap items-center gap-2">
              {testCases.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => handleCaseSelect(idx)}
                  className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${
                    selectedCaseIdx === idx
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                      : 'bg-ink-soft/60 text-slate-400 hover:text-slate-200 border border-transparent'
                  }`}
                >
                  Case {idx + 1}
                </button>
              ))}
            </div>

            {/* Input & Expected Details */}
            {currentCase && (
              <div className="space-y-3">
                <div>
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Input:
                  </p>
                  <pre className="rounded-lg border border-ink-line/60 bg-[#090d13] p-3 text-slate-200 overflow-x-auto">
                    {typeof currentCase.input === 'object'
                      ? Object.entries(currentCase.input)
                          .map(([k, v]) => `${k} = ${JSON.stringify(v)}`)
                          .join('\n')
                      : JSON.stringify(currentCase.input, null, 2)}
                  </pre>
                </div>

                <div>
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Expected:
                  </p>
                  <pre className="rounded-lg border border-ink-line/60 bg-[#090d13] p-2.5 text-emerald-300 overflow-x-auto">
                    {JSON.stringify(currentCase.expected)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'result' && (
          <div>
            {!runResult && !running && (
              <div className="flex flex-col items-center justify-center py-8 text-slate-500">
                <span className="text-2xl mb-1">⚡</span>
                <p>Click "Run" to test your solution.</p>
              </div>
            )}

            {running && (
              <div className="flex flex-col items-center justify-center py-8 text-sky-400 space-y-2">
                <span className="h-6 w-6 rounded-full border-2 border-sky-400 border-t-transparent animate-spin" />
                <p className="font-sans text-xs">Running…</p>
              </div>
            )}

            {runResult && !running && (
              <div className="space-y-4">
                {/* Result Header Badge */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#282828] pb-3">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`font-sans text-sm font-bold px-2.5 py-0.5 rounded-full ${
                        runResult.status === 'Accepted'
                          ? 'bg-[#2cbb5d]/15 text-[#2cbb5d] border border-[#2cbb5d]/40'
                          : 'bg-[#ff375f]/15 text-[#ff375f] border border-[#ff375f]/40'
                      }`}
                    >
                      {runResult.status}
                    </span>
                    <span className="text-[#8a8a8a] text-xs font-sans">
                      {runResult.passed_count}/{runResult.total_count} passed
                    </span>
                  </div>

                  <div className="text-slate-500 text-xs font-mono">
                    Runtime: <strong className="text-slate-300">{runResult.runtime_ms} ms</strong>
                  </div>
                </div>

                {/* Compile Error Banner */}
                {runResult.error && (
                  <div className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-3 text-rose-300">
                    <p className="font-bold mb-1">Error:</p>
                    <pre className="whitespace-pre-wrap">{runResult.error}</pre>
                  </div>
                )}

                {/* Student Authored Unit Tests Results */}
                {runResult.student_tests && runResult.student_tests.length > 0 && (
                  <div className="space-y-2 rounded-lg border border-sky-500/20 bg-sky-950/10 p-3">
                    <div className="flex items-center justify-between text-xs font-semibold text-sky-200">
                      <span className="flex items-center gap-1.5">
                        <span>🧪</span>
                        <span>Unit Tests</span>
                      </span>
                      <span className="text-[11px] font-mono text-sky-400">
                        {runResult.student_passed_count ?? 0}/{runResult.student_total_count ?? 0} passed
                      </span>
                    </div>

                    <div className="space-y-1.5 pt-1">
                      {runResult.student_tests.map((st: StudentTestResult, i: number) => (
                        <div
                          key={i}
                          className={`flex flex-col rounded-md border p-2 text-xs transition ${
                            st.passed
                              ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-200'
                              : 'border-rose-500/40 bg-rose-950/30 text-rose-200'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="flex items-center gap-2 font-medium">
                              <span
                                className={`flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold ${
                                  st.passed ? 'bg-emerald-500/30 text-emerald-300' : 'bg-rose-500/30 text-rose-300'
                                }`}
                              >
                                {st.passed ? '✓' : '✗'}
                              </span>
                              <span>{st.test_name}</span>
                            </span>
                            <span className="text-[10px] font-mono opacity-60">{st.runtime_ms} ms</span>
                          </div>
                          {st.error && (
                            <pre className="mt-1.5 rounded bg-black/40 p-1.5 font-mono text-[11px] text-rose-300 whitespace-pre-wrap">
                              {st.error}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Hidden Test Suite Selector */}
                {runResult.results.length > 0 && (
                  <div className="space-y-3">
                    <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      Test Cases:
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      {runResult.results.map((res, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleCaseSelect(idx)}
                          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold border transition ${
                            selectedCaseIdx === idx
                              ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                              : 'bg-ink-soft/40 text-slate-400 border-transparent hover:text-slate-200'
                          }`}
                        >
                          <span
                            className={`h-2 w-2 rounded-full ${
                              res.passed ? 'bg-emerald-400' : 'bg-rose-400'
                            }`}
                          />
                          Case {idx + 1}
                        </button>
                      ))}
                    </div>

                    {/* Detailed Case Output Diff */}
                    {currentResult && (
                      <div className="space-y-2">
                        {currentResult.error ? (
                          <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-2.5 text-rose-300">
                            <p className="text-[10px] text-rose-400 font-bold mb-0.5">
                              Error:
                            </p>
                            <pre className="whitespace-pre-wrap">{currentResult.error}</pre>
                          </div>
                        ) : (
                          <>
                            <div className="grid gap-2 sm:grid-cols-2">
                              <div>
                                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                                  Your Output:
                                </p>
                                <pre
                                  className={`rounded-lg border p-2.5 overflow-x-auto ${
                                    currentResult.passed
                                      ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300'
                                      : 'border-rose-500/30 bg-rose-950/20 text-rose-300'
                                  }`}
                                >
                                  {JSON.stringify(currentResult.actual)}
                                </pre>
                              </div>

                              <div>
                                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                                  Expected Output:
                                </p>
                                <pre className="rounded-lg border border-ink-line/60 bg-[#090d13] p-2.5 text-slate-300 overflow-x-auto">
                                  {JSON.stringify(currentResult.expected)}
                                </pre>
                              </div>
                            </div>

                            {/* Stdout if available */}
                            {currentResult.stdout && (
                              <div>
                                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                                  Stdout:
                                </p>
                                <pre className="rounded-lg border border-ink-line/60 bg-[#090d13] p-2 text-slate-400 whitespace-pre-wrap">
                                  {currentResult.stdout}
                                </pre>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
