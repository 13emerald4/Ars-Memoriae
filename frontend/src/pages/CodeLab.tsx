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
import { FullscreenButton } from '../components/FullscreenContext'

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
  const [layoutMode, setLayoutMode] = useState<'split' | 'code' | 'problem'>('split')
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

  // Popover toggles in Left Pane
  const [showTopics, setShowTopics] = useState(false)
  const [showHints, setShowHints] = useState(false)

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
        setShowTopics(false)
        setShowHints(false)
      })
      .catch((err) => {
        if (active) setError(err)
      })

    api
      .listCodeSubmissions(undefined, 15)
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

  const handleShuffle = () => {
    if (problems.length === 0) return
    const randIdx = Math.floor(Math.random() * problems.length)
    setSelectedSlug(problems[randIdx].slug)
  }

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
        api.listCodeSubmissions(undefined, 15),
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

  const isCurrentSolved =
    problemDetail &&
    (submissions.some((s) => s.problem_id === problemDetail.id && s.status === 'Accepted') ||
      problems.find((p) => p.slug === problemDetail.slug)?.last_status === 'Accepted')

  return (
    <div className="flex flex-col space-y-3">
      <ErrorNote error={error} />

      {/* ── 1. LEETCODE GLOBAL TOP NAVIGATION BAR ── */}
      <header className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#282828] bg-[#1a1a1a] px-3.5 py-2 shadow-md">
        {/* Left: Problem Navigator (Blind 75 selector + < > arrows + Shuffle) */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setViewMode('workbench')}
            className="flex items-center gap-1.5 text-xs font-bold text-[#eff1f6] hover:text-[#2cbb5d] transition pr-1"
            title="LeetCode Problem Studio"
          >
            <span className="text-[#ffa116] text-base font-extrabold">⚡</span>
          </button>

          {/* Categorized Dropdown Selector */}
          <div className="relative">
            <select
              value={selectedSlug || ''}
              onChange={(e) => {
                setSelectedSlug(e.target.value)
                setViewMode('workbench')
              }}
              className="rounded-lg border border-[#333333] bg-[#262626] px-3 py-1.5 text-xs font-bold text-[#eff1f6] focus:border-[#2cbb5d] focus:outline-none max-w-[280px] sm:max-w-[320px] cursor-pointer truncate"
            >
              {groupedCategories.map((group) => (
                <optgroup
                  key={group.category}
                  label={`${group.icon} ${group.category} (${group.solved}/${group.total})`}
                  className="bg-[#1e1e1e] text-[#569cd6] font-bold"
                >
                  {group.problems.map((p) => (
                    <option
                      key={p.slug}
                      value={p.slug}
                      className="bg-[#1a1a1a] text-[#eff1f6] font-normal"
                    >
                      {p.last_status === 'Accepted' ? '✅' : p.has_submission ? '🟡' : '⚪'}{' '}
                      {p.difficulty === 'Easy' ? '🟢' : p.difficulty === 'Medium' ? '🟡' : '🔴'}{' '}
                      {p.title}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Prev / Next navigation */}
          <button
            disabled={!prevProblem}
            onClick={() => prevProblem && setSelectedSlug(prevProblem.slug)}
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#333333] bg-[#262626] text-xs font-bold text-[#eff1f6] hover:bg-[#333333] disabled:opacity-30 transition"
            title={prevProblem ? `Previous: ${prevProblem.title}` : 'No previous problem'}
          >
            &lt;
          </button>
          <button
            disabled={!nextProblem}
            onClick={() => nextProblem && setSelectedSlug(nextProblem.slug)}
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#333333] bg-[#262626] text-xs font-bold text-[#eff1f6] hover:bg-[#333333] disabled:opacity-30 transition"
            title={nextProblem ? `Next: ${nextProblem.title}` : 'No next problem'}
          >
            &gt;
          </button>

          {/* Shuffle button */}
          <button
            onClick={handleShuffle}
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#333333] bg-[#262626] text-xs text-[#8a8a8a] hover:text-[#eff1f6] hover:bg-[#333333] transition"
            title="Pick Random Problem (Shuffle)"
          >
            🔀
          </button>
        </div>

        {/* Center: Run & Submit Buttons (LeetCode style) */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleRun}
            disabled={running || submitting}
            className="flex items-center gap-1.5 rounded-lg border border-[#3a3a3a] bg-[#262626] hover:bg-[#333333] px-3.5 py-1 text-xs font-semibold text-[#eff1f6] transition disabled:opacity-40"
            title="Run Code (Ctrl+Enter)"
          >
            <span className="text-xs text-[#8a8a8a]">▶</span>
            <span>{running ? 'Running…' : 'Run'}</span>
          </button>

          <button
            onClick={handleSubmit}
            disabled={running || submitting}
            className="flex items-center gap-1.5 rounded-lg bg-[#2cbb5d] hover:bg-[#2cbb5d]/90 px-4 py-1 text-xs font-bold text-white shadow transition disabled:opacity-40"
            title="Submit Code (Ctrl+Shift+Enter)"
          >
            <span>☁️</span>
            <span>{submitting ? 'Submitting…' : 'Submit'}</span>
          </button>

          {/* Reflex Timer */}
          <div className="hidden md:flex items-center gap-1 rounded-lg border border-[#2d2d2d] bg-[#1e1e1e] px-2.5 py-1 text-xs font-mono text-[#8a8a8a]">
            <span>⏱</span>
            <span className="font-bold text-[#eff1f6]">{formatTimer(timerSec)}</span>
            <button
              onClick={() => setTimerActive((a) => !a)}
              className="text-[10px] text-[#8a8a8a] hover:text-[#eff1f6] ml-0.5"
            >
              {timerActive ? '⏸' : '▶'}
            </button>
          </div>
        </div>

        {/* Right: View switcher & AI Tools */}
        <div className="flex items-center gap-1.5 text-xs">
          <div className="flex items-center rounded-lg border border-[#2d2d2d] bg-[#1e1e1e] p-0.5">
            <button
              onClick={() => {
                setViewMode('workbench')
                setLayoutMode('split')
              }}
              title="50/50 Split View (Problem on left, Code editor on right)"
              className={`rounded px-2.5 py-1 text-xs font-semibold transition flex items-center gap-1 ${
                viewMode === 'workbench' && layoutMode === 'split'
                  ? 'bg-[#2cbb5d] text-white shadow'
                  : 'text-[#8a8a8a] hover:text-[#eff1f6]'
              }`}
            >
              <span>◫</span>
              <span>50/50 Split</span>
            </button>
            <button
              onClick={() => {
                setViewMode('workbench')
                setLayoutMode('code')
              }}
              title="Full width Code Editor"
              className={`rounded px-2 py-1 text-xs font-semibold transition hidden sm:inline ${
                viewMode === 'workbench' && layoutMode === 'code'
                  ? 'bg-[#2cbb5d] text-white shadow'
                  : 'text-[#8a8a8a] hover:text-[#eff1f6]'
              }`}
            >
              Code Only
            </button>
            <button
              onClick={() => setViewMode('tree')}
              className={`rounded px-2.5 py-1 text-xs font-semibold transition ${
                viewMode === 'tree'
                  ? 'bg-[#2cbb5d] text-white shadow'
                  : 'text-[#8a8a8a] hover:text-[#eff1f6]'
              }`}
            >
              Tree
            </button>
            <button
              onClick={() => setViewMode('roadmap')}
              className={`rounded px-2.5 py-1 text-xs font-semibold transition ${
                viewMode === 'roadmap'
                  ? 'bg-[#2cbb5d] text-white shadow'
                  : 'text-[#8a8a8a] hover:text-[#eff1f6]'
              }`}
            >
              Roadmap
            </button>
            <button
              onClick={() => setViewMode('stats')}
              className={`rounded px-2.5 py-1 text-xs font-semibold transition ${
                viewMode === 'stats'
                  ? 'bg-[#2cbb5d] text-white shadow'
                  : 'text-[#8a8a8a] hover:text-[#eff1f6]'
              }`}
            >
              Metrics
            </button>
          </div>

          <button
            onClick={() => setForgeOpen(true)}
            className="hidden sm:flex items-center gap-1 rounded-lg border border-[#333333] bg-[#262626] px-2.5 py-1 text-xs font-semibold text-[#ffa116] hover:bg-[#333333] transition"
            title="Forge custom challenge with AI"
          >
            ✨ Forge
          </button>
          <FullscreenButton size="sm" />
        </div>
      </header>

      {exportMsg && (
        <div className="rounded-lg bg-[#2cbb5d]/10 border border-[#2cbb5d]/30 px-3 py-1.5 text-xs font-semibold text-[#2cbb5d]">
          {exportMsg}
        </div>
      )}

      {/* ── 2. VIEW: LEETCODE SPLIT-PANE WORKBENCH (DEFAULT) ── */}
      {viewMode === 'workbench' && problemDetail && (
        <div
          className={`grid gap-3 min-h-[680px] ${
            layoutMode === 'split' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'
          }`}
        >
          {/* ── LEFT PANE: DESCRIPTION, EDITORIAL, SOLUTIONS, SUBMISSIONS, SOCRATIC ── */}
          {(layoutMode === 'split' || layoutMode === 'problem') && (
            <div className="flex flex-col rounded-xl border border-[#282828] bg-[#1a1a1a] overflow-hidden shadow-2xl">
            {/* LeetCode Tab Bar */}
            <div className="flex items-center gap-1 border-b border-[#282828] bg-[#262626] px-3 py-1.5 text-xs">
              {(
                [
                  ['description', '📋 Description'],
                  ['editorial', '💡 Editorial'],
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
                      ? 'bg-[#1a1a1a] text-[#eff1f6] font-semibold shadow'
                      : 'text-[#8a8a8a] hover:text-[#eff1f6]'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Left Pane Scrollable Body */}
            <div className="flex-1 p-5 overflow-y-auto max-h-[720px] text-xs text-[#d4d4d4] leading-relaxed space-y-4">
              {/* TAB 1: DESCRIPTION */}
              {activeTab === 'description' && (
                <div className="space-y-4">
                  {/* Problem Title & Solved Checkmark */}
                  <div className="flex items-baseline justify-between gap-2 border-b border-[#282828] pb-3">
                    <h1 className="text-lg font-bold text-[#eff1f6] tracking-tight">
                      {problemDetail.title}
                    </h1>

                    {isCurrentSolved && (
                      <span className="flex items-center gap-1 text-xs font-semibold text-[#2cbb5d]">
                        <span>✓</span> Solved
                      </span>
                    )}
                  </div>

                  {/* Metadata Chips: Difficulty, Topics, Hints */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        problemDetail.difficulty === 'Easy'
                          ? 'text-[#00b8a3] bg-[#00b8a3]/10 border border-[#00b8a3]/30'
                          : problemDetail.difficulty === 'Medium'
                          ? 'text-[#ffc01e] bg-[#ffc01e]/10 border border-[#ffc01e]/30'
                          : 'text-[#ff375f] bg-[#ff375f]/10 border border-[#ff375f]/30'
                      }`}
                    >
                      {problemDetail.difficulty}
                    </span>

                    <button
                      onClick={() => setShowTopics((s) => !s)}
                      className="rounded-full bg-[#282828] hover:bg-[#333333] border border-[#3a3a3a] px-2.5 py-0.5 text-xs text-[#8a8a8a] hover:text-[#eff1f6] transition flex items-center gap-1"
                    >
                      <span>🏷️ Topics</span>
                      <span className="text-[9px]">{showTopics ? '▲' : '▼'}</span>
                    </button>

                    {problemDetail.hints.length > 0 && (
                      <button
                        onClick={() => setShowHints((h) => !h)}
                        className="rounded-full bg-[#282828] hover:bg-[#333333] border border-[#3a3a3a] px-2.5 py-0.5 text-xs text-[#8a8a8a] hover:text-[#eff1f6] transition flex items-center gap-1"
                      >
                        <span>💡 Hint</span>
                        <span className="text-[9px]">{showHints ? '▲' : '▼'}</span>
                      </button>
                    )}

                    {decks.length > 0 && (
                      <select
                        onChange={(e) => {
                          if (e.target.value) handleExportCard(e.target.value)
                        }}
                        defaultValue=""
                        className="rounded-full bg-[#282828] border border-[#3a3a3a] px-2.5 py-0.5 text-xs text-[#8a8a8a] focus:outline-none cursor-pointer"
                      >
                        <option value="" disabled>
                          ➕ Add to Deck…
                        </option>
                        {decks.map((d) => (
                          <option key={d.id} value={d.id} className="bg-[#1a1a1a] text-[#eff1f6]">
                            {d.name}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  {/* Topics Popover Drawer */}
                  {showTopics && (
                    <div className="flex flex-wrap items-center gap-1.5 p-2.5 rounded-lg bg-[#222222] border border-[#333333]">
                      <span className="rounded bg-[#2cbb5d]/15 text-[#2cbb5d] font-semibold px-2 py-0.5 text-[11px]">
                        {problemDetail.category}
                      </span>
                      {problemDetail.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded bg-[#282828] text-[#eff1f6] px-2 py-0.5 text-[11px]"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Hints Popover Drawer */}
                  {showHints && problemDetail.hints.length > 0 && (
                    <div className="space-y-2 p-3 rounded-lg bg-[#222222] border border-[#333333]">
                      {problemDetail.hints.map((hint, idx) => (
                        <div key={idx} className="text-xs text-[#d4d4d4]">
                          <strong className="text-[#ffa116]">Hint {idx + 1}:</strong> {hint}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Problem Description Content */}
                  <div className="prose prose-invert text-xs whitespace-pre-wrap leading-relaxed text-[#eff1f6]">
                    {problemDetail.description}
                  </div>

                  {/* Examples (Formatted in LeetCode Box) */}
                  <div className="space-y-3 pt-2">
                    {problemDetail.examples.map((ex, idx) => (
                      <div key={idx} className="space-y-1">
                        <p className="font-bold text-[#eff1f6] text-xs">Example {idx + 1}:</p>
                        <div className="space-y-1.5 rounded-lg border border-[#333333] bg-[#222222]/70 p-3 font-mono text-xs">
                          <div>
                            <span className="font-bold text-[#8a8a8a]">Input: </span>
                            <span className="text-[#eff1f6]">{ex.input}</span>
                          </div>
                          <div>
                            <span className="font-bold text-[#8a8a8a]">Output: </span>
                            <span className="text-[#eff1f6]">{ex.output}</span>
                          </div>
                          {ex.explanation && (
                            <div className="pt-1 text-[#8a8a8a] text-[11px] font-sans">
                              <span className="font-bold text-[#8a8a8a]">Explanation: </span>
                              {ex.explanation}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Constraints */}
                  {problemDetail.constraints.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <p className="font-bold text-[#eff1f6] text-xs">Constraints:</p>
                      <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-[#eff1f6] bg-[#222222]/40 rounded-lg p-3 border border-[#333333]/60">
                        {problemDetail.constraints.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: EDITORIAL */}
              {activeTab === 'editorial' && (
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-[#00b8a3]">
                    💡 Algorithmic Intuition & Complexity Proof
                  </h3>
                  {problemDetail.editorial ? (
                    <div className="prose prose-invert text-xs whitespace-pre-wrap leading-relaxed text-[#eff1f6]">
                      {problemDetail.editorial}
                    </div>
                  ) : (
                    <p className="text-[#8a8a8a] italic">No editorial written yet.</p>
                  )}
                </div>
              )}

              {/* TAB 3: SOLUTIONS */}
              {activeTab === 'solutions' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-[#2cbb5d]">
                    ✨ Canonical Solutions
                  </h3>
                  {Object.entries(problemDetail.solutions).map(([lang, solCode]) => (
                    <div key={lang} className="space-y-1">
                      <p className="font-bold text-xs uppercase text-[#8a8a8a]">{lang}</p>
                      <pre className="rounded-lg border border-[#333333] bg-[#222222] p-3 text-xs text-[#eff1f6] font-mono overflow-x-auto whitespace-pre">
                        {solCode}
                      </pre>
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 4: SUBMISSIONS */}
              {activeTab === 'submissions' && (
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-[#eff1f6]">📊 Submissions History</h3>
                  {submissions.length === 0 ? (
                    <p className="text-[#8a8a8a] italic">No submissions recorded yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {submissions.map((sub) => (
                        <div
                          key={sub.id}
                          className="flex items-center justify-between rounded-lg border border-[#333333] bg-[#222222] p-2.5 text-xs font-mono"
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className={`font-bold ${
                                sub.status === 'Accepted' ? 'text-[#2cbb5d]' : 'text-[#ff375f]'
                              }`}
                            >
                              {sub.status}
                            </span>
                            <span className="text-[#8a8a8a]">
                              ({sub.passed_tests}/{sub.total_tests})
                            </span>
                          </div>
                          <div className="text-[#8a8a8a] text-[11px]">
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

              {/* TAB 5: SOCRATIC AI */}
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
          )}

          {/* ── RIGHT PANE: CODE EDITOR & TEST CONSOLE (LEETCODE STACK) ── */}
          {(layoutMode === 'split' || layoutMode === 'code') && (
            <div className="flex flex-col space-y-3">
              {/* Editor Container */}
              <div className="flex-1 min-h-[420px]">
                <CodeEditor
                  code={code}
                  onChange={(val) => setCode(val)}
                  language={language}
                  onLanguageChange={(lang) => setLanguage(lang)}
                  onRun={handleRun}
                  onSubmit={handleSubmit}
                  running={running}
                  submitting={submitting}
                  height="420px"
                />
              </div>

              {/* Test Console Container */}
              <div>
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
          )}
        </div>
      )}

      {/* ── 3. VIEW: TREE DIAGRAM HIERARCHY ── */}
      {viewMode === 'tree' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#282828] bg-[#1a1a1a] p-3">
            <div className="flex items-center gap-2">
              <button
                onClick={expandAllBranches}
                className="btn btn-secondary px-3 py-1 text-xs font-semibold text-[#eff1f6]"
              >
                📂 Expand All Trees
              </button>
              <button
                onClick={collapseAllBranches}
                className="btn btn-secondary px-3 py-1 text-xs font-semibold text-[#eff1f6]"
              >
                📁 Collapse All
              </button>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value)}
                className="rounded-lg border border-[#333333] bg-[#262626] px-2.5 py-1 text-xs text-[#eff1f6] focus:outline-none"
              >
                <option value="All">All Difficulties</option>
                <option value="Easy">🟢 Easy</option>
                <option value="Medium">🟡 Medium</option>
                <option value="Hard">🔴 Hard</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="rounded-lg border border-[#333333] bg-[#262626] px-2.5 py-1 text-xs text-[#eff1f6] focus:outline-none"
              >
                <option value="All">All Statuses</option>
                <option value="Solved">✅ Solved Only</option>
                <option value="Todo">⚪ Todo Only</option>
              </select>
            </div>
          </div>

          <div className="rounded-2xl border border-[#282828] bg-[#1a1a1a] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#282828] pb-3">
              <div>
                <h2 className="text-base font-bold text-[#eff1f6]">
                  Blind 75 Curriculum Tree Hierarchy
                </h2>
                <p className="text-xs text-[#8a8a8a]">
                  18 canonical category branches sorting {problems.length} problem subtrees by conceptual prerequisites.
                </p>
              </div>
              <span className="text-xs font-mono font-bold text-[#2cbb5d]">
                {solvedCount} / {totalProblemsCount} Solved ({solvedPct}%)
              </span>
            </div>

            <div className="space-y-3 font-mono">
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
                  <div key={branch.category} className="text-xs">
                    {/* Category Branch Node */}
                    <div
                      onClick={() => toggleBranch(branch.category)}
                      className="flex cursor-pointer items-center justify-between rounded-xl border border-[#282828] bg-[#262626]/70 px-4 py-2 hover:border-[#3a3a3a] hover:bg-[#262626] transition select-none"
                    >
                      <div className="flex items-center gap-2.5 font-sans">
                        <span className="text-[#8a8a8a] font-mono text-sm">
                          {isLastBranch ? '└──' : '├──'}
                        </span>
                        <span className="text-base">{branch.icon}</span>
                        <span className="font-bold text-[#eff1f6] text-sm">{branch.category}</span>
                        <span className="text-xs text-[#8a8a8a]">
                          ({branch.solved}/{branch.total} solved)
                        </span>
                      </div>

                      <div className="flex items-center gap-3 font-sans">
                        <div className="hidden sm:flex h-2 w-24 overflow-hidden rounded-full bg-[#1e1e1e]">
                          <div
                            className="h-full rounded-full bg-[#2cbb5d] transition-all duration-300"
                            style={{ width: `${branch.pct}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-[#569cd6]">
                          {isExpanded ? '▼ collapse' : '▶ expand'}
                        </span>
                      </div>
                    </div>

                    {/* Problem Subtree Nodes */}
                    {isExpanded && (
                      <div className="ml-5 border-l-2 border-[#333333] pl-4 pt-2 space-y-1 font-sans">
                        {branchProblems.length === 0 ? (
                          <div className="text-[11px] text-[#8a8a8a] italic py-1 pl-4">
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
                                className={`flex cursor-pointer items-center justify-between rounded-lg px-3 py-1.5 text-xs transition select-none ${
                                  isSelected
                                    ? 'border border-[#2cbb5d]/60 bg-[#2cbb5d]/10 text-[#eff1f6]'
                                    : 'border border-[#282828] bg-[#1e1e1e]/60 text-[#d4d4d4] hover:bg-[#262626]'
                                }`}
                              >
                                <div className="flex items-center gap-2.5 truncate pr-2">
                                  <span className="font-mono text-[#8a8a8a] text-xs">
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
                                        ? 'text-[#00b8a3] bg-[#00b8a3]/10'
                                        : p.difficulty === 'Medium'
                                        ? 'text-[#ffc01e] bg-[#ffc01e]/10'
                                        : 'text-[#ff375f] bg-[#ff375f]/10'
                                    }`}
                                  >
                                    {p.difficulty}
                                  </span>
                                  <button className="btn btn-primary px-2 py-0.5 text-[11px] bg-[#2cbb5d] hover:bg-[#2cbb5d]/90 text-white font-medium">
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

      {/* ── 4. VIEW: ROADMAP EXPLORER ── */}
      {viewMode === 'roadmap' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#282828] bg-[#1a1a1a] p-3">
            <div className="flex flex-1 items-center gap-2 min-w-[240px]">
              <span className="text-[#8a8a8a]">🔍</span>
              <input
                type="text"
                placeholder="Search Blind 75 problems..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent text-xs text-[#eff1f6] placeholder-[#8a8a8a] focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="rounded-lg border border-[#333333] bg-[#262626] px-2.5 py-1 text-xs text-[#eff1f6] focus:outline-none"
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
                className="rounded-lg border border-[#333333] bg-[#262626] px-2.5 py-1 text-xs text-[#eff1f6] focus:outline-none"
              >
                <option value="All">All Difficulties</option>
                <option value="Easy">🟢 Easy</option>
                <option value="Medium">🟡 Medium</option>
                <option value="Hard">🔴 Hard</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
                  className="flex flex-col rounded-xl border border-[#282828] bg-[#1a1a1a] p-4 shadow hover:border-[#3a3a3a] transition"
                >
                  <div className="flex items-start justify-between gap-2 border-b border-[#282828] pb-2.5">
                    <div>
                      <div className="flex items-center gap-2">
                        <span>{cat.icon}</span>
                        <h3 className="text-sm font-bold text-[#eff1f6]">{cat.name}</h3>
                      </div>
                      <p className="mt-0.5 text-[11px] text-[#8a8a8a]">{cat.desc}</p>
                    </div>
                    <span className="chip text-[11px] font-bold border-[#00b8a3]/30 bg-[#00b8a3]/10 text-[#00b8a3]">
                      {solvedCat}/{totalCat}
                    </span>
                  </div>

                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#262626]">
                    <div
                      className="h-full rounded-full bg-[#2cbb5d] transition-all duration-300"
                      style={{ width: `${catPct}%` }}
                    />
                  </div>

                  <div className="mt-2.5 flex-1 space-y-1 overflow-y-auto max-h-[220px] pr-1">
                    {catProbs.map((p) => (
                      <div
                        key={p.slug}
                        onClick={() => {
                          setSelectedSlug(p.slug)
                          setViewMode('workbench')
                        }}
                        className="flex cursor-pointer items-center justify-between rounded-lg p-1.5 text-xs border border-[#282828] bg-[#222222]/50 hover:bg-[#262626] transition"
                      >
                        <div className="flex items-center gap-1.5 truncate pr-2">
                          <span>{p.last_status === 'Accepted' ? '✅' : '⚪'}</span>
                          <span className="truncate font-medium text-[#eff1f6]">{p.title}</span>
                        </div>
                        <span
                          className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            p.difficulty === 'Easy'
                              ? 'text-[#00b8a3] bg-[#00b8a3]/10'
                              : p.difficulty === 'Medium'
                              ? 'text-[#ffc01e] bg-[#ffc01e]/10'
                              : 'text-[#ff375f] bg-[#ff375f]/10'
                          }`}
                        >
                          {p.difficulty}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── 5. VIEW: LEARNING METRICS ── */}
      {viewMode === 'stats' && codeStats && (
        <div className="space-y-6">
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

          <VelocityCard velocity={codeStats.velocity} />

          <Section
            title="Coding Activity Heatmap"
            description="Submissions logged per day across all Blind 75 algorithmic challenges."
          >
            <HeatmapGrid data={codeStats.heatmap} />
          </Section>

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
                      <span className="w-16 text-xs text-[#8a8a8a] font-mono">{bucket}</span>
                      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-[#262626]">
                        <div
                          className="h-full rounded-full bg-[#2cbb5d] transition-all duration-300"
                          style={{ width: `${rate * 100}%` }}
                        />
                      </div>
                      <span className="w-12 text-right text-xs tabular-nums text-[#eff1f6] font-bold">
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
              <ForecastBars data={codeStats.forecast} color="bg-[#00b8a3]/70" />
            </Section>
          </div>

          <CodingLeeches
            leeches={codeStats.leeches}
            onSelect={(slug) => {
              setSelectedSlug(slug)
              setViewMode('workbench')
            }}
          />
        </div>
      )}

      {/* AI Problem Forge Modal */}
      {forgeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-[#333333] bg-[#1a1a1a] p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-[#eff1f6]">✨ Forge Custom Problem with AI</h3>
            <p className="text-xs text-[#8a8a8a]">
              Generate a brand new challenge or targeted drill using Qwen 2.5 Coder.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-[#eff1f6] block mb-1">Topic or Concept:</label>
                <input
                  type="text"
                  placeholder="e.g. Invert a 3D matrix, Trie with wildcard, Monotonic queue"
                  value={forgeTopic}
                  onChange={(e) => setForgeTopic(e.target.value)}
                  className="w-full rounded-xl border border-[#333333] bg-[#262626] px-3 py-2 text-[#eff1f6] focus:outline-none focus:border-[#2cbb5d]"
                />
              </div>

              <div>
                <label className="font-semibold text-[#eff1f6] block mb-1">Target Difficulty:</label>
                <select
                  value={forgeDifficulty}
                  onChange={(e) => setForgeDifficulty(e.target.value)}
                  className="w-full rounded-xl border border-[#333333] bg-[#262626] px-3 py-2 text-[#eff1f6] focus:outline-none"
                >
                  <option value="Easy">🟢 Easy</option>
                  <option value="Medium">🟡 Medium</option>
                  <option value="Hard">🔴 Hard</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setForgeOpen(false)}
                disabled={forging}
                className="btn btn-secondary px-3 py-1.5 text-xs text-[#eff1f6]"
              >
                Cancel
              </button>
              <button
                onClick={handleForge}
                disabled={forging || !forgeTopic.trim()}
                className="btn btn-primary px-3.5 py-1.5 text-xs bg-[#2cbb5d] hover:bg-[#2cbb5d]/90 text-white font-bold"
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
 * Helper Components Matching LeetCode Dark Theme
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
    <div className="card bg-[#1a1a1a] border border-[#282828]" title={hint}>
      <p className="text-xs uppercase tracking-wide text-[#8a8a8a]">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-[#eff1f6]">
        {Math.round(value).toLocaleString()}
        {suffix && <span className="ml-0.5 text-base text-[#8a8a8a]">{suffix}</span>}
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
        <div className="rounded-xl border border-[#282828] bg-[#1e1e1e] p-3">
          <p className="text-xs text-[#8a8a8a]">Velocity Rate</p>
          <p className="text-xl font-bold text-[#2cbb5d] tabular-nums">{rate} / hr</p>
        </div>
        <div className="rounded-xl border border-[#282828] bg-[#1e1e1e] p-3">
          <p className="text-xs text-[#8a8a8a]">Mastered Total</p>
          <p className="text-xl font-bold text-[#eff1f6] tabular-nums">{total} problems</p>
        </div>
        <div className="rounded-xl border border-[#282828] bg-[#1e1e1e] p-3">
          <p className="text-xs text-[#8a8a8a]">Active Practice Time</p>
          <p className="text-xl font-bold text-[#569cd6] tabular-nums">{hours} hours</p>
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
    if (n === 0) return 'bg-[#282828]'
    const r = n / max
    if (r > 0.66) return 'bg-[#2cbb5d]'
    if (r > 0.33) return 'bg-[#2cbb5d]/70'
    return 'bg-[#2cbb5d]/40'
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
            <div key={l.problem_id} className="rounded-xl border border-[#282828] p-4 bg-[#1e1e1e]">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="chip text-[#ff375f] border-[#ff375f]/30 bg-[#ff375f]/10 font-bold">
                    {l.lapse_count} failed attempts
                  </span>
                  <span className="chip text-[#eff1f6] font-semibold">{l.category}</span>
                  <span
                    className={`chip font-semibold ${
                      l.difficulty === 'Easy'
                        ? 'text-[#00b8a3] bg-[#00b8a3]/10 border-[#00b8a3]/40'
                        : l.difficulty === 'Medium'
                        ? 'text-[#ffc01e] bg-[#ffc01e]/10 border-[#ffc01e]/40'
                        : 'text-[#ff375f] bg-[#ff375f]/10 border-[#ff375f]/40'
                    }`}
                  >
                    {l.difficulty}
                  </span>
                </div>
                <button
                  onClick={() => onSelect(l.slug)}
                  className="btn btn-primary px-3 py-1 text-xs bg-[#2cbb5d] hover:bg-[#2cbb5d]/90 text-white font-bold"
                >
                  🛠️ Practice with Socratic AI
                </button>
              </div>

              <h4 className="mt-2 text-sm font-bold text-[#eff1f6]">{l.title}</h4>

              {l.last_error && (
                <p className="mt-1 text-xs font-mono text-[#ff375f]">
                  Last Failure Status: <strong>{l.last_error}</strong>
                </p>
              )}

              <div className="mt-2.5 rounded-lg border border-[#333333] bg-[#222222] p-3">
                <p className="text-xs text-[#8a8a8a]">{l.suggestion_rationale}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
