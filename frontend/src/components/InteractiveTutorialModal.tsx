import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../hooks/useAuth'

interface Props {
  isOpen: boolean
  onClose: () => void
  initialMode?: 'prompt' | 'tour'
}

export default function InteractiveTutorialModal({
  isOpen,
  onClose,
  initialMode = 'prompt',
}: Props) {
  const navigate = useNavigate()
  const { user, refresh } = useAuth()
  const [step, setStep] = useState(0) // 0 to 5
  const [mode, setMode] = useState<'prompt' | 'tour'>(initialMode)
  const [simulatedAnswer, setSimulatedAnswer] = useState(
    'Encapsulation bundles state and methods together while hiding internal implementation details behind a public interface.'
  )
  const [isGrading, setIsGrading] = useState(false)
  const [gradedResult, setGradedResult] = useState<null | {
    grade: 'good'
    confidence: number
    matched: string[]
    missed: string[]
    reasoning: string
  }>(null)
  const [selectedTreeChapter, setSelectedTreeChapter] = useState(0)
  const [retentionSlider, setRetentionSlider] = useState(90)

  // Reset state when opened
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode)
      setStep(0)
      setGradedResult(null)
    }
  }, [isOpen, initialMode])

  const finishTutorial = useCallback(
    async (targetRoute?: string) => {
      try {
        localStorage.removeItem('prompt_new_user_tutorial')
        localStorage.setItem('tutorial_prompt_dismissed', 'true')
        if (user && !user.tutorial_completed) {
          await api.updateMe({ tutorial_completed: true })
          await refresh()
        }
      } catch (err) {
        console.error('Failed to update tutorial completion status:', err)
      } finally {
        onClose()
        if (targetRoute) {
          navigate(targetRoute)
        }
      }
    },
    [user, refresh, onClose, navigate]
  )

  const handleSimulateGrading = () => {
    setIsGrading(true)
    setGradedResult(null)
    setTimeout(() => {
      setIsGrading(false)
      setGradedResult({
        grade: 'good',
        confidence: 0.94,
        matched: [
          'Bundling data and methods into a cohesive unit',
          'Information hiding (preventing unauthorized external mutation)',
        ],
        missed: ['Explicit mention of access modifiers (private/protected)'],
        reasoning:
          'Clear, concise, and accurate conceptual explanation. Correctly identified both packaging and interface boundary contracts.',
      })
    }, 700)
  }

  // Keyboard navigation (Arrow keys & Esc)
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        void finishTutorial()
      } else if (mode === 'tour') {
        if (e.key === 'ArrowRight' && step < 5) {
          setStep((s) => s + 1)
        } else if (e.key === 'ArrowLeft' && step > 0) {
          setStep((s) => s - 1)
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, mode, step, finishTutorial])

  if (!isOpen) return null

  // 1. Initial Welcome Prompt Mode
  if (mode === 'prompt') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-md animate-in fade-in duration-200">
        <div className="w-full max-w-lg rounded-2xl border border-sky-500/40 bg-[#0d131f] p-6 shadow-2xl space-y-5 text-slate-200">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-500/20 text-2xl border border-sky-500/30 shadow-inner">
              🏛️
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400">
                Welcome to Ars Memoriae
              </span>
              <h2 className="text-lg font-bold text-slate-100">Take the Interactive Tour?</h2>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            Welcome, <strong className="text-sky-300">{user?.email ?? 'scholar'}</strong>! Your
            spaced-repetition workspace is ready.
          </p>

          <div className="rounded-xl border border-ink-line bg-ink/70 p-4 space-y-2.5 text-xs text-slate-300">
            <div className="flex items-start gap-2.5">
              <span className="text-emerald-400 text-sm">✓</span>
              <span>
                <strong className="text-slate-100">Active Recall:</strong> Type your answers with local
                AI evaluation instead of passive self-grading.
              </span>
            </div>
            <div className="flex items-start gap-2.5">
              <span className="text-sky-400 text-sm">✓</span>
              <span>
                <strong className="text-slate-100">Knowledge Tree:</strong> Organize decks hierarchically
                with drag-and-drop branch reordering and visual distribution bars.
              </span>
            </div>
            <div className="flex items-start gap-2.5">
              <span className="text-amber-400 text-sm">✓</span>
              <span>
                <strong className="text-slate-100">Priority Queue:</strong> Daily time budgets with zero
                unbounded card backlogs.
              </span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2.5 pt-1">
            <button
              type="button"
              onClick={() => setMode('tour')}
              className="btn btn-primary flex-1 py-2.5 text-xs font-semibold shadow-lg shadow-sky-500/20"
            >
              Start Interactive Tour (2 min) →
            </button>
            <button
              type="button"
              onClick={() => void finishTutorial()}
              className="btn py-2.5 text-xs text-slate-400 hover:text-slate-200"
            >
              Skip for now
            </button>
          </div>

          <p className="text-center text-[11px] text-slate-500">
            You can always relaunch this tour from the <strong className="text-slate-400">Start here</strong> navigation tab.
          </p>
        </div>
      </div>
    )
  }

  // 2. Multi-Step Interactive Tour Mode
  const steps = [
    {
      title: 'Active Recall & The FSRS Engine',
      badge: 'Core Philosophy',
      icon: '🧠',
    },
    {
      title: 'Live AI Grading Simulator',
      badge: 'Active Recall',
      icon: '🤖',
    },
    {
      title: 'Knowledge Tree & Progress Bars',
      badge: 'Hierarchy & Structure',
      icon: '🌲',
    },
    {
      title: 'Priority Queue & Time Bank',
      badge: 'Cognitive Load',
      icon: '⏱️',
    },
    {
      title: 'Incremental Reading & Code Lab',
      badge: 'Deep Mastery',
      icon: '📖',
    },
    {
      title: "You're Ready to Master Your Mind",
      badge: 'Next Steps',
      icon: '🚀',
    },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-2xl max-h-[92vh] rounded-2xl border border-sky-500/30 bg-[#0d131f] shadow-2xl text-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-ink-line px-6 py-4 bg-ink-soft/40 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{steps[step].icon}</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="chip border-sky-500/40 text-sky-300 text-[10px] font-bold uppercase tracking-wider">
                  {steps[step].badge}
                </span>
                <span className="text-xs text-slate-500">
                  Step {step + 1} of {steps.length}
                </span>
              </div>
              <h2 className="text-base font-bold text-slate-100">{steps[step].title}</h2>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void finishTutorial()}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition"
            title="Close walkthrough"
          >
            ✕
          </button>
        </div>

        {/* Progress Bar */}
        <div className="h-1 w-full bg-slate-800 shrink-0">
          <div
            className="h-full bg-gradient-to-r from-sky-500 to-emerald-400 transition-all duration-300"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>

        {/* Body Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1 text-xs">
          {/* STEP 0: FSRS & Active Recall */}
          {step === 0 && (
            <div className="space-y-4">
              <p className="text-slate-300 leading-relaxed">
                Conventional flashcard apps rely on <strong className="text-amber-300">passive recognition</strong>:
                you look at the prompt, flip the card, and guess whether you knew it. But the cognitive science
                of learning proves that true retention requires <strong className="text-emerald-300">effortful active retrieval</strong>.
              </p>

              <div className="rounded-xl border border-ink-line bg-ink-soft/60 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">Interactive FSRS Retention Target Simulator</span>
                  <span className="font-mono text-sky-300 font-bold">{retentionSlider}% Target</span>
                </div>
                <input
                  type="range"
                  min="75"
                  max="97"
                  value={retentionSlider}
                  onChange={(e) => setRetentionSlider(Number(e.target.value))}
                  className="w-full accent-sky-500 cursor-pointer"
                />
                <div className="grid grid-cols-3 gap-2 text-center text-[11px] pt-1">
                  <div className="rounded-lg bg-black/40 p-2 border border-ink-line">
                    <span className="block text-slate-400 text-[10px]">Optimal Review Interval</span>
                    <span className="font-bold text-emerald-400 text-xs">
                      {Math.round(18 * ((100 - retentionSlider) / 10))} Days
                    </span>
                  </div>
                  <div className="rounded-lg bg-black/40 p-2 border border-ink-line">
                    <span className="block text-slate-400 text-[10px]">Retention Stability</span>
                    <span className="font-bold text-sky-400 text-xs">
                      {(retentionSlider * 0.96).toFixed(1)}% Memory
                    </span>
                  </div>
                  <div className="rounded-lg bg-black/40 p-2 border border-ink-line">
                    <span className="block text-slate-400 text-[10px]">Daily Review Load</span>
                    <span className="font-bold text-amber-300 text-xs">
                      {Math.round(20 * (retentionSlider / 85))} min/day
                    </span>
                  </div>
                </div>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Ars Memoriae uses <strong className="text-slate-200">py-fsrs</strong> to track stability, difficulty,
                  and retrievability per item, automatically smoothing your schedule so you never face sudden backlogs.
                </p>
              </div>
            </div>
          )}

          {/* STEP 1: Live AI Grading Simulator */}
          {step === 1 && (
            <div className="space-y-3.5">
              <p className="text-slate-300 leading-relaxed">
                When you review a card, you type your answer. A local LLM running privately on your machine
                grades your typed reasoning against the reference answer, verified in real-time by a
                <strong className="text-sky-300"> token-by-token answer similarity checker</strong>.
              </p>

              {/* Sample Card */}
              <div className="rounded-xl border border-sky-500/30 bg-ink-soft/80 p-4 space-y-3">
                <div className="flex items-center justify-between text-[11px] text-slate-400 border-b border-ink-line pb-2">
                  <span className="font-semibold text-sky-300">Sample Active Recall Card</span>
                  <span className="chip text-[10px]">CPSC 210 · Ch 12</span>
                </div>

                <div>
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Question:
                  </label>
                  <p className="text-sm font-semibold text-slate-100">
                    What is encapsulation in software engineering, and why is it important?
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Your Typed Answer:
                    </label>
                    <button
                      type="button"
                      onClick={() =>
                        setSimulatedAnswer(
                          'Encapsulation bundles data with functions that manipulate that data, restricting direct access from outside.'
                        )
                      }
                      className="text-[10px] text-sky-400 hover:text-sky-300 underline"
                    >
                      Fill sample answer
                    </button>
                  </div>
                  <textarea
                    rows={2}
                    value={simulatedAnswer}
                    onChange={(e) => setSimulatedAnswer(e.target.value)}
                    className="input font-sans text-xs w-full resize-none"
                    placeholder="Type your explanation here..."
                  />
                </div>

                <button
                  type="button"
                  onClick={handleSimulateGrading}
                  disabled={isGrading}
                  className="btn btn-primary w-full py-1.5 text-xs font-semibold"
                >
                  {isGrading ? 'AI Evaluating Reasoning…' : 'Simulate AI Grading ⚡'}
                </button>

                {gradedResult && (
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3 space-y-2.5 animate-in fade-in duration-200">
                    <div className="flex items-center justify-between">
                      <span className="chip border-emerald-500/40 text-emerald-300 font-bold uppercase text-[10px]">
                        Grade: {gradedResult.grade.toUpperCase()} ({(gradedResult.confidence * 100).toFixed(0)}% Confidence)
                      </span>
                      <span className="text-[10px] text-slate-400">100% Local (Qwen 2.5 Coder)</span>
                    </div>
                    <p className="text-[11px] text-slate-300 italic">"{gradedResult.reasoning}"</p>
                    <div className="text-[10px] space-y-1 text-slate-300">
                      <p className="text-emerald-300 font-medium">✓ Matched: {gradedResult.matched.join(', ')}</p>
                      <p className="text-amber-300/80 font-medium">△ Missed: {gradedResult.missed.join(', ')}</p>
                    </div>

                    {/* Token-by-token answer similarity checker highlight */}
                    <div className="rounded border border-sky-500/30 bg-black/40 p-2 space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-semibold text-sky-300 flex items-center gap-1">
                          🔍 Token-by-Token Answer Similarity Checker
                        </span>
                        <span className="font-mono text-emerald-400 font-bold">88% Lexical Overlap</span>
                      </div>
                      <p className="text-[10px] text-slate-400 leading-tight">
                        Runs parallel token-level Jaccard and n-gram verification against the reference answer to prevent AI grading discrepancies.
                      </p>
                    </div>

                    <p className="text-[10px] text-slate-400 pt-1 border-t border-emerald-500/20">
                      💡 You can always confirm or override the AI grade with the four standard Again/Hard/Good/Easy buttons.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 2: Knowledge Tree */}
          {step === 2 && (
            <div className="space-y-3.5">
              <p className="text-slate-300 leading-relaxed">
                Rather than treating all flashcards as a flat list, Ars Memoriae implements a unified
                <strong className="text-sky-300"> Knowledge Tree</strong> with drag-and-drop branch reordering and
                hierarchical distribution metrics.
              </p>

              <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-4 space-y-3">
                <span className="text-[11px] font-semibold text-slate-200 block">
                  Interactive Deck & Branch Hierarchy Demo
                </span>

                <div className="space-y-1.5 font-sans">
                  {/* Root Node */}
                  <div className="rounded-lg border border-sky-500/30 bg-sky-950/20 px-3 py-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sky-400 font-bold">🏛️</span>
                      <span className="font-semibold text-sky-200 text-xs">CPSC 210 — Software Construction</span>
                    </div>
                    <span className="chip text-[10px] border-sky-500/30 text-sky-300">Root Course</span>
                  </div>

                  {/* Child Chapters */}
                  {[
                    { title: 'Ch 08: Designing for Failure', viewed: '85%', diff: 'Medium', pos: 1 },
                    { title: 'Ch 09: Validating Behaviour', viewed: '60%', diff: 'Hard', pos: 2 },
                    { title: 'Ch 10: Building Abstractions', viewed: '100%', diff: 'Easy', pos: 3 },
                  ].map((ch, idx) => (
                    <div
                      key={ch.title}
                      onClick={() => setSelectedTreeChapter(idx)}
                      className={`ml-5 rounded-lg border px-3 py-2 transition-all flex items-center justify-between cursor-pointer ${
                        selectedTreeChapter === idx
                          ? 'border-sky-500/50 bg-sky-900/30 text-slate-100'
                          : 'border-ink-line bg-ink/80 text-slate-300 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500 font-mono text-[10px]">#{ch.pos}</span>
                        <span className="font-medium text-xs">{ch.title}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Micro distribution bar preview */}
                        <div className="flex h-2 w-16 overflow-hidden rounded bg-slate-800" title="Progress Bar">
                          <div className="bg-emerald-400" style={{ width: ch.viewed }} />
                          <div className="bg-amber-400" style={{ width: '15%' }} />
                          <div className="bg-slate-700" style={{ width: '10%' }} />
                        </div>
                        <span className="text-[10px] font-mono text-slate-400">{ch.viewed}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg bg-black/40 p-2.5 text-[11px] text-slate-300 space-y-1">
                  <p>
                    📊 <strong className="text-emerald-300">Hierarchical Rollup:</strong> Viewing a parent deck
                    summarizes the entire course across <em>Cards Viewed</em>, <em>Difficulty</em>, and <em>Recall Ratings</em>.
                  </p>
                  <p>
                    🔀 <strong className="text-sky-300">Drag & Drop:</strong> In the Tree view, you can drag branches
                    and subdecks directly to rearrange study order according to your syllabus.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Priority Queue & Time Bank */}
          {step === 3 && (
            <div className="space-y-3.5">
              <p className="text-slate-300 leading-relaxed">
                Backlog anxiety is the #1 reason learners abandon spaced repetition. In Ars Memoriae, you never face
                an infinite list of overdue cards.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🎯</span>
                    <h4 className="font-semibold text-slate-200">Daily Time Budget</h4>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Set a daily budget (e.g. 20 or 30 minutes). The queue ranks cards by priority + overdue score
                    and fills your time budget. You study what matters most first.
                  </p>
                </div>

                <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🏦</span>
                    <h4 className="font-semibold text-slate-200">The Time Bank</h4>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Target card goals within study blocks. Finishing early deposits remaining minutes into your Time
                    Bank, directly rewarding mastery velocity over passive seat time.
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3.5 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-amber-300 font-bold">📝 Metacognitive Reflection</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  After finishing a study block, you briefly note any external distractions and state your plan for
                  the next block. This closes the executive-function loop and boosts cognitive retention.
                </p>
              </div>
            </div>
          )}

          {/* STEP 4: Incremental Reading & Code Lab */}
          {step === 4 && (
            <div className="space-y-3.5">
              <p className="text-slate-300 leading-relaxed">
                Two unique pillars empower deep technical learning and comprehensive document mastery:
              </p>

              <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-4 space-y-2.5">
                <div className="flex items-center gap-2 text-sky-300 font-semibold">
                  <span>📄</span>
                  <span>Incremental Reading (IR)</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Paste textbook chapters, scientific papers, or documentation URLs. Ars Memoriae chunks the text
                  into paragraph extracts with verified source page citations, interleaving reading extracts with your
                  flashcard queue.
                </p>
              </div>

              <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-4 space-y-2.5">
                <div className="flex items-center gap-2 text-emerald-300 font-semibold">
                  <span>💻</span>
                  <span>Interactive Code Lab & Socratic Guide</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Practice coding challenges directly in your browser with automated test suite execution. Stuck?
                  The Socratic Guide asks clarifying questions to guide you toward the algorithmic insight without spoiling
                  the solution.
                </p>
              </div>
            </div>
          )}

          {/* STEP 5: Ready to Begin! */}
          {step === 5 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4 text-center space-y-2">
                <span className="text-3xl">🎉</span>
                <h3 className="text-sm font-bold text-emerald-200">You're All Set!</h3>
                <p className="text-xs text-slate-300 max-w-md mx-auto">
                  You now understand the core philosophy behind Ars Memoriae: Active Recall, FSRS scheduling,
                  hierarchical Knowledge Trees, and local AI reasoning.
                </p>
              </div>

              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                Where would you like to start?
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => void finishTutorial('/decks')}
                  className="rounded-xl border border-ink-line bg-ink-soft/80 p-3.5 text-left hover:border-sky-500/60 hover:bg-sky-950/20 transition group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-200 group-hover:text-sky-300 text-xs">
                      1. Decks & Cards
                    </span>
                    <span className="text-sky-400 text-xs group-hover:translate-x-0.5 transition-transform">→</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Create decks or import starter notes from JSON.</p>
                </button>

                <button
                  type="button"
                  onClick={() => void finishTutorial('/tree')}
                  className="rounded-xl border border-ink-line bg-ink-soft/80 p-3.5 text-left hover:border-sky-500/60 hover:bg-sky-950/20 transition group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-200 group-hover:text-sky-300 text-xs">
                      2. Knowledge Tree
                    </span>
                    <span className="text-sky-400 text-xs group-hover:translate-x-0.5 transition-transform">→</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Explore knowledge branches and arrange study order.</p>
                </button>

                <button
                  type="button"
                  onClick={() => void finishTutorial('/tutorial')}
                  className="rounded-xl border border-ink-line bg-ink-soft/80 p-3.5 text-left hover:border-sky-500/60 hover:bg-sky-950/20 transition group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-200 group-hover:text-sky-300 text-xs">
                      3. Milestone Checklist
                    </span>
                    <span className="text-sky-400 text-xs group-hover:translate-x-0.5 transition-transform">→</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Track your verified learning telemetry & milestones.</p>
                </button>

                <button
                  type="button"
                  onClick={() => void finishTutorial('/review')}
                  className="rounded-xl border border-ink-line bg-ink-soft/80 p-3.5 text-left hover:border-sky-500/60 hover:bg-sky-950/20 transition group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-200 group-hover:text-sky-300 text-xs">
                      4. Review Queue
                    </span>
                    <span className="text-sky-400 text-xs group-hover:translate-x-0.5 transition-transform">→</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Jump right into active recall review sessions.</p>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between border-t border-ink-line px-6 py-4 bg-ink-soft/40 shrink-0">
          <button
            type="button"
            disabled={step === 0}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            className="btn px-3 py-1.5 text-xs text-slate-300 hover:text-slate-100 disabled:opacity-30"
          >
            ← Previous
          </button>

          {/* Dots Indicator */}
          <div className="flex items-center gap-1.5">
            {steps.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setStep(i)}
                className={`h-2 rounded-full transition-all ${
                  i === step
                    ? 'w-6 bg-sky-400'
                    : 'w-2 bg-slate-700 hover:bg-slate-500'
                }`}
                title={`Go to step ${i + 1}`}
              />
            ))}
          </div>

          {step < steps.length - 1 ? (
            <button
              type="button"
              onClick={() => setStep((s) => Math.min(steps.length - 1, s + 1))}
              className="btn btn-primary px-4 py-1.5 text-xs font-semibold"
            >
              Next →
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void finishTutorial('/review')}
              className="btn btn-primary px-4 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500/50"
            >
              Finish Tour ✓
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
