import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type {
  CodeLeech,
  CodeProblemOut,
  CodeProblemSummary,
  CodeProgressionStats,
  CodeSubmissionOut,
  Deck,
  RunCodeResponse,
  SubmitCodeResponse,
} from '../api/types'
import { CodeEditor } from '../components/CodeEditor'
import { CodeSocraticTutor } from '../components/CodeSocraticTutor'
import { CodeTestConsole } from '../components/CodeTestConsole'
import { Empty, ErrorNote, Section, Spinner } from '../components/ui'

const BLIND75_CATEGORIES = [
  { name: 'Arrays & Hashing', icon: '🗃️', desc: 'Hash maps, frequency counters, and prefix products' },
  { name: 'Two Pointers', icon: '🎯', desc: 'Converging or sliding pointer pairs on arrays/strings' },
  { name: 'Sliding Window', icon: '🪟', desc: 'Dynamic or fixed-size sub-segment optimization' },
  { name: 'Stack', icon: '🥞', desc: 'LIFO structure, monotonic stacks, bracket matching' },
  { name: 'Binary Search', icon: '🔍', desc: 'Logarithmic search on sorted or rotated spaces' },
  { name: 'Linked List', icon: '🔗', desc: 'Pointer manipulation, cycle detection, reordering' },
  { name: 'Trees', icon: '🌲', desc: 'DFS, BFS, BST invariants, LCA, and traversals' },
  { name: 'Tries', icon: '🌿', desc: 'Prefix trees for efficient prefix search and wildcards' },
  { name: 'Heap / Priority Queue', icon: '🏔️', desc: 'Dynamic order statistics and stream median' },
  { name: 'Backtracking', icon: '🔄', desc: 'Combinatorial decision trees and matrix searches' },
  { name: 'Graphs', icon: '🕸️', desc: 'Connected components, topological sort, cycle detection' },
  { name: 'Advanced Graphs', icon: '🛰️', desc: 'Lexicographical order & alien alphabet precedence' },
  { name: '1-D Dynamic Programming', icon: '📈', desc: 'Subproblem memoization, state transitions' },
  { name: '2-D Dynamic Programming', icon: '📊', desc: 'Grid paths, subsequence alignments' },
  { name: 'Greedy', icon: '⚡', desc: 'Locally optimal choices (Kadane, Jump Game)' },
  { name: 'Intervals', icon: '⏱️', desc: 'Merging, non-overlapping scheduling, room allocation' },
  { name: 'Math & Geometry', icon: '📐', desc: 'Matrix transpositions, spiral traversals, set zeroes' },
  { name: 'Bit Manipulation', icon: '0️⃣1️⃣', desc: 'Bitwise XOR cancellations, Hamming weights, shifts' },
]

export default function CodeLab() {
  const [viewMode, setViewMode] = useState<'workbench' | 'tree' | 'roadmap' | 'stats'>('workbench')
  const [problems, setProblems] = useState<CodeProblemSummary[]>([])
  const [codeStats, setCodeStats] = useState<CodeProgressionStats | null>(null)
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

  // Filters & Search
  const [categoryFilter, setCategoryFilter] = useState<string>('All')
  const [difficultyFilter, setDifficultyFilter] = useState<string>('All')
  const [statusFilter, setStatusFilter] = useState<'All' | 'Solved' | 'Todo'>('All')
  const [searchQuery, setSearchQuery] = useState<string>('')

  // Tree View Expand / Collapse State
  const [expandedBranches, setExpandedBranches] = useState<Set<string>>(
    new Set(BLIND75_CATEGORIES.map((c) => c.name)),
  )

  // Speed-run Timer
  const [timerSec, setTimerSec] = useState(0)
  const [timerActive, setTimerActive] = useState(false)

  // AI Forge Modal State
  const [forgeOpen, setForgeOpen] = useState(false)
  const [forgeTopic, setForgeTopic] = useState('')
  const [forgeDifficulty, setForgeDifficulty] = useState('Medium')
  const [forging, setForging] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [list, statsData, dList] = await Promise.all([
        api.listCodeProblems({ kind: 'problem' }),
        api.getCodeStats().catch(() => null),
        api.decks().catch(() => []),
      ])
      setProblems(list)
      setCodeStats(statsData)
      setDecks(dList)
      if (list.length > 0 && !selectedSlug) {
        setSelectedSlug(list[0].slug)
      }
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [selectedSlug])

  useEffect(() => {
    void loadData()
  }, [loadData])

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

  // Filtered problems list
  const filteredProblems = useMemo(() => {
    return problems.filter((p) => {
      if (categoryFilter !== 'All' && p.category !== categoryFilter) return false
      if (difficultyFilter !== 'All' && p.difficulty !== difficultyFilter) return false
      if (statusFilter === 'Solved' && p.last_status !== 'Accepted') return false
      if (statusFilter === 'Todo' && p.last_status === 'Accepted') return false
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        if (!p.title.toLowerCase().includes(q) && !p.slug.toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [problems, categoryFilter, difficultyFilter, statusFilter, searchQuery])

  // Grouped problems by category for Tree structure & sorted optgroup dropdown
  const groupedCategories = useMemo(() => {
    const map = new Map<string, CodeProblemSummary[]>()
    for (const cat of BLIND75_CATEGORIES) {
      map.set(cat.name, [])
    }
    for (const p of problems) {
      const list = map.get(p.category)
      if (list) {
        list.push(p)
      } else {
        map.set(p.category, [p])
      }
    }
    return BLIND75_CATEGORIES.map((cat) => {
      const catProbs = map.get(cat.name) || []
      const solved = catProbs.filter((p) => p.last_status === 'Accepted').length
      return {
        category: cat.name,
        icon: cat.icon,
        desc: cat.desc,
        problems: catProbs,
        total: catProbs.length,
        solved,
        pct: catProbs.length > 0 ? Math.round((solved / catProbs.length) * 100) : 0,
      }
    }).filter((group) => group.total > 0)
  }, [problems])

  // Sequential Next / Prev navigation
  const currentIndex = problems.findIndex((p) => p.slug === selectedSlug)
  const prevProblem = currentIndex > 0 ? problems[currentIndex - 1] : null
  const nextProblem =
    currentIndex >= 0 && currentIndex < problems.length - 1 ? problems[currentIndex + 1] : null

  const toggleBranch = (categoryName: string) => {
    setExpandedBranches((prev) => {
      const next = new Set(prev)
      if (next.has(categoryName)) {
        next.delete(categoryName)
      } else {
        next.add(categoryName)
      }
      return next
    })
  }

  const expandAllBranches = () => {
    setExpandedBranches(new Set(BLIND75_CATEGORIES.map((c) => c.name)))
  }

  const collapseAllBranches = () => {
    setExpandedBranches(new Set())
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
      const [subs, refreshedStats, refreshedList] = await Promise.all([
        api.listCodeSubmissions(undefined, 10),
        api.getCodeStats().catch(() => null),
        api.listCodeProblems({ kind: 'problem' }),
      ])
      setSubmissions(subs)
      setCodeStats(refreshedStats)
      setProblems(refreshedList)
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
      await loadData()
      setSelectedSlug(newProb.slug)
      setViewMode('workbench')
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

  const totalProblemsCount = codeStats?.totals.cards ?? problems.length
  const solvedCount =
    codeStats?.totals.solved ?? problems.filter((p) => p.last_status === 'Accepted').length
  const solvedPct =
    totalProblemsCount > 0 ? Math.round((solvedCount / totalProblemsCount) * 100) : 0

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />

      {/* ── Blind 75 Master Navigation & Progress Banner ── */}
      <div className="rounded-2xl border border-ink-line bg-[#0d1117] p-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-line/80 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold tracking-tight text-slate-100">
                ⚡ Blind 75 Problem Studio
              </span>
              <span className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[11px] font-bold text-amber-300">
                Curated High-Yield
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              Master the essential 75 algorithmic patterns for technical interviews with FSRS retention & Socratic AI.
            </p>
          </div>

          {/* View Mode Switcher */}
          <div className="flex items-center gap-1 rounded-xl border border-ink-line bg-[#161b22] p-1">
            <button
              onClick={() => setViewMode('workbench')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                viewMode === 'workbench'
                  ? 'bg-sky-500 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>⚡</span> Workbench
            </button>
            <button
              onClick={() => setViewMode('tree')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                viewMode === 'tree'
                  ? 'bg-sky-500 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>🌳</span> Tree Diagram
            </button>
            <button
              onClick={() => setViewMode('roadmap')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                viewMode === 'roadmap'
                  ? 'bg-sky-500 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>🗺️</span> Roadmap
            </button>
            <button
              onClick={() => setViewMode('stats')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                viewMode === 'stats'
                  ? 'bg-sky-500 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>📈</span> Learning Metrics
            </button>
          </div>
        </div>

        {/* Global Progress Bar & Tier Breakdown */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-baseline gap-1.5">
              <span className="text-lg font-bold text-slate-100">{solvedCount}</span>
              <span className="text-xs text-slate-400">/ {totalProblemsCount} solved</span>
              <span className="ml-1 text-xs font-bold text-emerald-400">({solvedPct}%)</span>
            </div>
            <div className="h-2.5 w-36 overflow-hidden rounded-full bg-[#161b22] border border-ink-line">
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-sky-400 transition-all duration-500"
                style={{ width: `${Math.max(4, solvedPct)}%` }}
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-medium text-emerald-300">
              🟢 Easy: {codeStats?.difficulty.easy?.solved ?? 0}/{codeStats?.difficulty.easy?.total ?? 0}
            </span>
            <span className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-medium text-amber-300">
              🟡 Medium: {codeStats?.difficulty.medium?.solved ?? 0}/{codeStats?.difficulty.medium?.total ?? 0}
            </span>
            <span className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 font-medium text-rose-300">
              🔴 Hard: {codeStats?.difficulty.hard?.solved ?? 0}/{codeStats?.difficulty.hard?.total ?? 0}
            </span>
            {codeStats?.totals.avg_stability_days && (
              <span
                className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-2 py-0.5 font-medium text-sky-300"
                title="Days until recall falls to 90%"
              >
                ⏱️ Stability: {Math.round(codeStats.totals.avg_stability_days)}d
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── VIEW 1: INTERACTIVE TREE DIAGRAM (Hierarchical Problem Trees) ── */}
      {viewMode === 'tree' && (
        <div className="space-y-6">
          {/* Tree Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink-line bg-[#0d1117] p-3">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={expandAllBranches}
                className="btn btn-secondary px-3 py-1 text-xs font-semibold"
              >
                📂 Expand All Trees
              </button>
              <button
                onClick={collapseAllBranches}
                className="btn btn-secondary px-3 py-1 text-xs font-semibold"
              >
                📁 Collapse All
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value)}
                className="rounded-lg border border-ink-line bg-[#161b22] px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value="All">All Difficulties</option>
                <option value="Easy">🟢 Easy</option>
                <option value="Medium">🟡 Medium</option>
                <option value="Hard">🔴 Hard</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="rounded-lg border border-ink-line bg-[#161b22] px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value="All">All Statuses</option>
                <option value="Solved">✅ Solved Only</option>
                <option value="Todo">⚪ Todo Only</option>
              </select>
            </div>
          </div>

          {/* Root Tree Diagram Card */}
          <div className="rounded-2xl border border-ink-line bg-[#0d1117] p-6 shadow-2xl space-y-6">
            <div className="flex items-center gap-3 border-b border-ink-line/80 pb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/20 text-xl border border-sky-500/30">
                🌳
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-100">
                  Blind 75 Curriculum Tree Hierarchy
                </h2>
                <p className="text-xs text-slate-400">
                  18 canonical category branches sorting {problems.length} problem subtrees by conceptual prerequisites.
                </p>
              </div>
            </div>

            {/* Tree Branch Hierarchy */}
            <div className="space-y-4 font-mono">
              {groupedCategories.map((branch, branchIdx) => {
                const isLastBranch = branchIdx === groupedCategories.length - 1
                const isExpanded = expandedBranches.has(branch.category)
                const branchProblems = branch.problems.filter((p) => {
                  if (difficultyFilter !== 'All' && p.difficulty !== difficultyFilter) return false
                  if (statusFilter === 'Solved' && p.last_status !== 'Accepted') return false
                  if (statusFilter === 'Todo' && p.last_status === 'Accepted') return false
                  return true
                })

                return (
                  <div key={branch.category} className="group text-xs">
                    {/* Category Branch Node */}
                    <div
                      onClick={() => toggleBranch(branch.category)}
                      className="flex cursor-pointer items-center justify-between rounded-xl border border-ink-line/70 bg-[#161b22]/70 px-4 py-2.5 hover:border-sky-500/50 hover:bg-[#161b22] transition select-none"
                    >
                      <div className="flex items-center gap-2.5 font-sans">
                        <span className="text-slate-500 font-mono text-sm">
                          {isLastBranch ? '└──' : '├──'}
                        </span>
                        <span className="text-base">{branch.icon}</span>
                        <span className="font-bold text-slate-100 text-sm">{branch.category}</span>
                        <span className="text-xs text-slate-500">
                          ({branch.solved}/{branch.total} solved)
                        </span>
                      </div>

                      <div className="flex items-center gap-3 font-sans">
                        <div className="hidden sm:flex h-2 w-24 overflow-hidden rounded-full bg-ink-line">
                          <div
                            className="h-full rounded-full bg-emerald-400 transition-all duration-300"
                            style={{ width: `${branch.pct}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-sky-300">
                          {isExpanded ? '▼ collapse' : '▶ expand'}
                        </span>
                      </div>
                    </div>

                    {/* Subtrees: Actual Problem Nodes */}
                    {isExpanded && (
                      <div className="ml-5 border-l-2 border-slate-700/60 pl-4 pt-2 space-y-1.5 font-sans">
                        {branchProblems.length === 0 ? (
                          <div className="text-[11px] text-slate-500 italic py-1 pl-4">
                            No problems match the current filter in this branch.
                          </div>
                        ) : (
                          branchProblems.map((p, pIdx) => {
                            const isLastProblem = pIdx === branchProblems.length - 1
                            const isSelected = selectedSlug === p.slug
                            const isSolved = p.last_status === 'Accepted'

                            return (
                              <div
                                key={p.slug}
                                onClick={() => {
                                  setSelectedSlug(p.slug)
                                  setViewMode('workbench')
                                }}
                                className={`flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-xs transition select-none ${
                                  isSelected
                                    ? 'border border-sky-500/60 bg-sky-500/15 text-sky-200'
                                    : 'border border-ink-line/40 bg-[#090d13]/60 text-slate-300 hover:border-ink-line hover:bg-[#161b22]'
                                }`}
                              >
                                <div className="flex items-center gap-2.5 truncate pr-2">
                                  <span className="font-mono text-slate-600 text-xs">
                                    {isLastProblem ? '└──' : '├──'}
                                  </span>
                                  <span className="text-xs">
                                    {isSolved ? '✅' : p.has_submission ? '🟡' : '⚪'}
                                  </span>
                                  <span className="truncate font-semibold">{p.title}</span>
                                </div>

                                <div className="flex items-center gap-2 shrink-0">
                                  <span
                                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                      p.difficulty === 'Easy'
                                        ? 'text-emerald-400 bg-emerald-500/10'
                                        : p.difficulty === 'Medium'
                                        ? 'text-amber-400 bg-amber-500/10'
                                        : 'text-rose-400 bg-rose-500/10'
                                    }`}
                                  >
                                    {p.difficulty}
                                  </span>
                                  <button className="btn btn-primary px-2 py-0.5 text-[11px] bg-sky-600 hover:bg-sky-500 text-white font-medium">
                                    Solve ➔
                                  </button>
                                </div>
                              </div>
                            )
                          })
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── VIEW 2: ROADMAP EXPLORER ── */}
      {viewMode === 'roadmap' && (
        <div className="space-y-6">
          {/* Search & Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink-line bg-[#0d1117] p-3">
            <div className="flex flex-1 items-center gap-2 min-w-[240px]">
              <span className="text-slate-500">🔍</span>
              <input
                type="text"
                placeholder="Search Blind 75 problems by title, tag, or number..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="rounded-lg border border-ink-line bg-[#161b22] px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value="All">All Categories ({BLIND75_CATEGORIES.length})</option>
                {BLIND75_CATEGORIES.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.icon} {c.name}
                  </option>
                ))}
              </select>

              <select
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value)}
                className="rounded-lg border border-ink-line bg-[#161b22] px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value="All">All Difficulties</option>
                <option value="Easy">🟢 Easy</option>
                <option value="Medium">🟡 Medium</option>
                <option value="Hard">🔴 Hard</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="rounded-lg border border-ink-line bg-[#161b22] px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value="All">All Statuses</option>
                <option value="Solved">✅ Solved Only</option>
                <option value="Todo">⚪ Todo Only</option>
              </select>
            </div>
          </div>

          {/* Categories Grid */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {BLIND75_CATEGORIES.filter(
              (cat) => categoryFilter === 'All' || cat.name === categoryFilter,
            ).map((cat) => {
              const catProbs = filteredProblems.filter((p) => p.category === cat.name)
              const totalCat = problems.filter((p) => p.category === cat.name).length
              const solvedCat = problems.filter(
                (p) => p.category === cat.name && p.last_status === 'Accepted',
              ).length
              const catPct = totalCat > 0 ? Math.round((solvedCat / totalCat) * 100) : 0

              return (
                <div
                  key={cat.name}
                  className="flex flex-col rounded-xl border border-ink-line bg-[#0d1117] p-4 shadow hover:border-ink-line/90 transition"
                >
                  <div className="flex items-start justify-between gap-2 border-b border-ink-line/60 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{cat.icon}</span>
                        <h3 className="text-sm font-bold text-slate-100">{cat.name}</h3>
                      </div>
                      <p className="mt-1 text-[11px] text-slate-400">{cat.desc}</p>
                    </div>
                    <span
                      className={`chip text-[11px] font-bold ${
                        catPct === 100
                          ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                          : 'border-sky-500/30 bg-sky-500/10 text-sky-300'
                      }`}
                    >
                      {solvedCat}/{totalCat}
                    </span>
                  </div>

                  {/* Category Progress Bar */}
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#161b22]">
                    <div
                      className="h-full rounded-full bg-emerald-400 transition-all duration-300"
                      style={{ width: `${catPct}%` }}
                    />
                  </div>

                  {/* Problems list */}
                  <div className="mt-3 flex-1 space-y-1.5 overflow-y-auto max-h-[260px] pr-1">
                    {catProbs.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic py-2">
                        No problems match the current filter.
                      </p>
                    ) : (
                      catProbs.map((p) => {
                        const isSelected = selectedSlug === p.slug
                        const isSolved = p.last_status === 'Accepted'
                        return (
                          <div
                            key={p.slug}
                            onClick={() => {
                              setSelectedSlug(p.slug)
                              setViewMode('workbench')
                            }}
                            className={`flex cursor-pointer items-center justify-between rounded-lg p-2 text-xs transition ${
                              isSelected
                                ? 'border border-sky-500/40 bg-sky-500/10 text-sky-200'
                                : 'border border-ink-line/40 bg-[#161b22]/50 text-slate-300 hover:bg-[#161b22] hover:text-slate-100'
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate pr-2">
                              <span className="text-xs">
                                {isSolved ? '✅' : p.has_submission ? '🟡' : '⚪'}
                              </span>
                              <span className="truncate font-medium">{p.title}</span>
                            </div>
                            <span
                              className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                                p.difficulty === 'Easy'
                                  ? 'text-emerald-400 bg-emerald-500/10'
                                  : p.difficulty === 'Medium'
                                  ? 'text-amber-400 bg-amber-500/10'
                                  : 'text-rose-400 bg-rose-500/10'
                              }`}
                            >
                              {p.difficulty}
                            </span>
                          </div>
                        )
                      })
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── VIEW 3: PROGRESSION & LEARNING METRICS (Mirroring Memorization Cards) ── */}
      {viewMode === 'stats' && codeStats && (
        <div className="space-y-8">
          {/* Topline Cards (identical to Stats.tsx §7) */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard label="Total Problems" value={codeStats.totals.cards} />
            <StatCard label="In Active Review" value={codeStats.totals.in_review} />
            <StatCard label="Submissions Logged" value={codeStats.totals.reviews_logged} />
            <StatCard
              label="Avg Stability"
              value={codeStats.totals.avg_stability_days}
              suffix="d"
              hint="Days until memory retention falls to 90%"
            />
            <StatCard
              label="Avg Difficulty"
              value={Math.round(codeStats.totals.avg_difficulty * 100)}
              suffix="%"
              hint="Overall difficulty weight across practice problems"
            />
          </div>

          {/* Velocity Dashboard (§ Velocity dashboard: mastered per active hour) */}
          <VelocityCard velocity={codeStats.velocity} />

          {/* 365-Day Practice Activity Heatmap */}
          <Section
            title="Coding Activity Heatmap"
            description="Submissions logged per day across all Blind 75 algorithmic challenges."
          >
            <HeatmapGrid data={codeStats.heatmap} />
          </Section>

          {/* Retention Curve & 30-Day Forecast */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Section
              title="Retention Curve"
              description="Repeat solve accuracy bucketed by time elapsed between attempts."
            >
              {Object.keys(codeStats.retention).length === 0 ? (
                <Empty title="Not enough repeat submission history yet." />
              ) : (
                <div className="space-y-2.5">
                  {Object.entries(codeStats.retention).map(([bucket, rate]) => (
                    <div key={bucket} className="flex items-center gap-3">
                      <span className="w-16 text-xs text-slate-400 font-mono">{bucket}</span>
                      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ink-line">
                        <div
                          className="h-full rounded-full bg-emerald-400/80 transition-all duration-300"
                          style={{ width: `${rate * 100}%` }}
                        />
                      </div>
                      <span className="w-12 text-right text-xs tabular-nums text-slate-300 font-bold">
                        {Math.round(rate * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section
              title="30-Day Spaced Review Forecast"
              description="Coding cards coming due for retention review over the next month."
            >
              <ForecastBars data={codeStats.forecast} color="bg-sky-400/70" />
            </Section>
          </div>

          {/* Coding Leeches & Repeated Lapses (§3.2 Remediation) */}
          <CodingLeeches
            leeches={codeStats.leeches}
            onSelect={(slug) => {
              setSelectedSlug(slug)
              setViewMode('workbench')
            }}
          />

          {/* Category Mastery Matrix */}
          <Section
            title="Category Mastery Progression"
            description="Comprehensive pattern coverage across all 18 Blind 75 topics."
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {codeStats.categories.map((c) => (
                <div
                  key={c.category}
                  onClick={() => {
                    setCategoryFilter(c.category)
                    setViewMode('roadmap')
                  }}
                  className="cursor-pointer rounded-xl border border-ink-line/60 bg-[#161b22]/60 p-3 hover:border-sky-500/40 transition"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{c.category}</span>
                    <span className="font-mono text-emerald-400 font-bold">
                      {c.solved}/{c.total} ({c.percentage}%)
                    </span>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-ink-line">
                    <div
                      className="h-full rounded-full bg-emerald-400 transition-all duration-300"
                      style={{ width: `${c.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}

      {/* ── VIEW 4: WORKBENCH SPLIT-PANE ── */}
      {viewMode === 'workbench' && (
        <div className="space-y-4">
          {/* Top Action & Navigation Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-line pb-4">
            <div className="flex flex-wrap items-center gap-2">
              {/* Sequential Prev & Next buttons */}
              <button
                disabled={!prevProblem}
                onClick={() => prevProblem && setSelectedSlug(prevProblem.slug)}
                className="btn btn-secondary px-2.5 py-1.5 text-xs font-semibold disabled:opacity-30"
                title={prevProblem ? `Previous: ${prevProblem.title}` : 'No previous problem'}
              >
                ◀ Prev
              </button>

              {/* Categorized Tree-Sorted Dropdown */}
              <select
                value={selectedSlug || ''}
                onChange={(e) => setSelectedSlug(e.target.value)}
                className="rounded-xl border border-ink-line bg-[#0d1117] px-3.5 py-2 text-sm font-semibold text-slate-100 focus:border-sky-500 focus:outline-none max-w-[360px]"
              >
                {groupedCategories.map((group) => (
                  <optgroup
                    key={group.category}
                    label={`${group.icon} ${group.category} (${group.solved}/${group.total})`}
                    className="bg-[#161b22] text-sky-300 font-bold"
                  >
                    {group.problems.map((p) => (
                      <option
                        key={p.slug}
                        value={p.slug}
                        className="bg-[#0d1117] text-slate-200 font-normal"
                      >
                        {p.last_status === 'Accepted' ? '✅' : p.has_submission ? '🟡' : '⚪'}{' '}
                        {p.difficulty === 'Easy' ? '🟢' : p.difficulty === 'Medium' ? '🟡' : '🔴'}{' '}
                        {p.title}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>

              <button
                disabled={!nextProblem}
                onClick={() => nextProblem && setSelectedSlug(nextProblem.slug)}
                className="btn btn-secondary px-2.5 py-1.5 text-xs font-semibold disabled:opacity-30"
                title={nextProblem ? `Next: ${nextProblem.title}` : 'No next problem'}
              >
                Next ▶
              </button>

              <button
                onClick={() => setViewMode('tree')}
                className="btn btn-secondary px-3 py-1.5 text-xs font-semibold text-emerald-300"
                title="Open full interactive tree hierarchy"
              >
                🌳 View Tree
              </button>

              <button
                onClick={() => setForgeOpen(true)}
                className="btn btn-secondary px-3 py-1.5 text-xs font-semibold text-sky-300"
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
                        <span className="chip border-slate-700 text-slate-300 font-semibold">
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

              {/* Right Pane (Code Editor & Test Harness Console) */}
              <div className="flex flex-col rounded-xl border border-ink-line bg-[#0d1117] overflow-hidden shadow-2xl">
                {/* Editor Header */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-line/80 bg-[#161b22] px-4 py-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-400">Language:</span>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="rounded-lg border border-ink-line bg-[#090d13] px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
                    >
                      <option value="python">Python 3</option>
                      <option value="typescript">TypeScript</option>
                    </select>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleRun}
                      disabled={running || submitting}
                      className="btn btn-secondary px-3 py-1.5 text-xs font-semibold"
                    >
                      {running ? 'Running…' : '▶ Run Code'}
                    </button>
                    <button
                      onClick={handleSubmit}
                      disabled={running || submitting}
                      className="btn btn-primary px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                    >
                      {submitting ? 'Submitting…' : '🚀 Submit'}
                    </button>
                  </div>
                </div>

                {/* Editor Area */}
                <div className="min-h-[380px] flex-1 bg-[#090d13]">
                  <CodeEditor
                    code={code}
                    onChange={(val) => setCode(val)}
                    language={language}
                    onLanguageChange={(lang) => setLanguage(lang)}
                    onRun={handleRun}
                    onSubmit={handleSubmit}
                    height="420px"
                  />
                </div>

                {/* Test Console */}
                <div className="border-t border-ink-line/80 bg-[#090d13] p-4">
                  <CodeTestConsole
                    testCases={problemDetail.test_cases || []}
                    runResult={runResult}
                    running={running}
                    onRun={handleRun}
                    onSubmit={handleSubmit}
                    submitting={submitting}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* AI Problem Forge Modal */}
      {forgeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-ink-line bg-[#0d1117] p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100">✨ Forge Custom Problem with AI</h3>
            <p className="text-xs text-slate-400">
              Generate a brand new canonical challenge or targeted drill using Gemini.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-300 block mb-1">Topic or Concept:</label>
                <input
                  type="text"
                  placeholder="e.g. Invert a 3D matrix, Trie with wildcard, Monotonic queue"
                  value={forgeTopic}
                  onChange={(e) => setForgeTopic(e.target.value)}
                  className="w-full rounded-xl border border-ink-line bg-[#161b22] px-3 py-2 text-slate-100 focus:outline-none"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-300 block mb-1">Target Difficulty:</label>
                <select
                  value={forgeDifficulty}
                  onChange={(e) => setForgeDifficulty(e.target.value)}
                  className="w-full rounded-xl border border-ink-line bg-[#161b22] px-3 py-2 text-slate-100 focus:outline-none"
                >
                  <option value="Easy">Easy</option>
                  <option value="Medium">Medium</option>
                  <option value="Hard">Hard</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setForgeOpen(false)}
                disabled={forging}
                className="btn btn-secondary px-3 py-1.5 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleForge}
                disabled={forging || !forgeTopic.trim()}
                className="btn btn-primary px-3.5 py-1.5 text-xs bg-sky-600 text-white"
              >
                {forging ? 'Forging Problem…' : 'Generate Challenge'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ────────────────────────────────────────────────────────────────────────────
 * Helper Components Matching the Rest of the Codebase (§7 Performance Metrics)
 * ──────────────────────────────────────────────────────────────────────────── */

function StatCard({
  label,
  value,
  suffix,
  hint,
}: {
  label: string
  value: number
  suffix?: string
  hint?: string
}) {
  return (
    <div className="card" title={hint}>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
        {Math.round(value).toLocaleString()}
        {suffix && <span className="ml-0.5 text-base text-slate-500">{suffix}</span>}
      </p>
    </div>
  )
}

function VelocityCard({ velocity }: { velocity: Record<string, number> }) {
  const rate = velocity.rate ?? 0
  const total = velocity.mastered_total ?? 0
  const hours = velocity.active_hours ?? 0

  return (
    <Section
      title="Mastery Velocity"
      description="Problems solved and consolidated per active practice hour (§ Velocity dashboard)."
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-ink-line/60 bg-[#161b22]/50 p-3">
          <p className="text-xs text-slate-400">Velocity Rate</p>
          <p className="text-xl font-bold text-emerald-400 tabular-nums">{rate} / hr</p>
        </div>
        <div className="rounded-xl border border-ink-line/60 bg-[#161b22]/50 p-3">
          <p className="text-xs text-slate-400">Mastered Total</p>
          <p className="text-xl font-bold text-slate-100 tabular-nums">{total} problems</p>
        </div>
        <div className="rounded-xl border border-ink-line/60 bg-[#161b22]/50 p-3">
          <p className="text-xs text-slate-400">Active Practice Time</p>
          <p className="text-xl font-bold text-sky-400 tabular-nums">{hours} hours</p>
        </div>
      </div>
    </Section>
  )
}

function HeatmapGrid({ data }: { data: Record<string, number> }) {
  const today = new Date()
  const days: { date: string; count: number }[] = []
  for (let i = 363; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    days.push({ date: key, count: data[key] ?? 0 })
  }
  const max = Math.max(1, ...days.map((d) => d.count))
  const level = (n: number) => {
    if (n === 0) return 'bg-ink-line'
    const r = n / max
    if (r > 0.66) return 'bg-emerald-400'
    if (r > 0.33) return 'bg-emerald-500/70'
    return 'bg-emerald-600/50'
  }

  const weeks: { date: string; count: number }[][] = []
  for (let i = 0; i < days.length; i += 7) weeks.push(days.slice(i, i + 7))

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex gap-[3px]">
        {weeks.map((week, i) => (
          <div key={i} className="flex flex-col gap-[3px]">
            {week.map((d) => (
              <span
                key={d.date}
                title={`${d.date}: ${d.count} submission${d.count === 1 ? '' : 's'}`}
                className={`h-2.5 w-2.5 rounded-[2px] ${level(d.count)}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function ForecastBars({ data, color }: { data: Record<string, number>; color: string }) {
  const entries = Object.entries(data).sort(([a], [b]) => a.localeCompare(b)).slice(0, 30)
  if (entries.length === 0) {
    return <Empty title="No upcoming reviews scheduled in the next 30 days." />
  }
  const max = Math.max(...entries.map(([, v]) => v))
  return (
    <div className="flex h-32 items-end gap-1">
      {entries.map(([date, count]) => (
        <div key={date} className="group relative flex-1" title={`${date}: ${count} due`}>
          <div
            className={`w-full rounded-t ${color}`}
            style={{ height: `${Math.max(3, (count / max) * 100)}%` }}
          />
        </div>
      ))}
    </div>
  )
}

function CodingLeeches({
  leeches,
  onSelect,
}: {
  leeches: CodeLeech[]
  onSelect: (slug: string) => void
}) {
  return (
    <Section
      title={`Coding Leeches (${leeches.length})`}
      description="Problems where test runs have failed repeatedly (§3.2). Targeted Socratic remediation prevents cognitive frustration."
    >
      {leeches.length === 0 ? (
        <Empty title="No coding leeches — zero stuck challenges detected." />
      ) : (
        <div className="space-y-3">
          {leeches.map((l) => (
            <div key={l.problem_id} className="rounded-xl border border-ink-line p-4 bg-[#161b22]/50">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="chip text-rose-300 border-rose-500/30 bg-rose-500/10 font-bold">
                    {l.lapse_count} failed attempts
                  </span>
                  <span className="chip text-slate-300 font-semibold">{l.category}</span>
                  <span
                    className={`chip ${
                      l.difficulty === 'Easy'
                        ? 'text-emerald-400'
                        : l.difficulty === 'Medium'
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {l.difficulty}
                  </span>
                </div>
                <button
                  onClick={() => onSelect(l.slug)}
                  className="btn btn-primary px-3 py-1 text-xs bg-sky-600 hover:bg-sky-500 text-white font-semibold"
                >
                  🛠️ Practice with Socratic AI
                </button>
              </div>

              <h4 className="mt-2 text-sm font-bold text-slate-100">{l.title}</h4>

              {l.last_error && (
                <p className="mt-1 text-xs font-mono text-rose-400">
                  Last Failure Status: <strong>{l.last_error}</strong>
                </p>
              )}

              <div className="mt-2.5 rounded-lg border border-sky-500/20 bg-sky-500/5 p-3">
                <p className="text-xs text-sky-200">{l.suggestion_rationale}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
