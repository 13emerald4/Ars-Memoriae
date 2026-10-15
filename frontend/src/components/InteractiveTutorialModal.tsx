import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../hooks/useAuth'

interface Props {
  isOpen: boolean
  onClose: () => void
  initialMode?: 'prompt' | 'tour'
  initialType?: 'extensive' | 'brief'
}

export default function InteractiveTutorialModal({
  isOpen,
  onClose,
  initialMode = 'prompt',
  initialType = 'extensive',
}: Props) {
  const navigate = useNavigate()
  const { user, refresh } = useAuth()
  const [step, setStep] = useState(0)
  const [mode, setMode] = useState<'prompt' | 'tour'>(initialMode)
  const [tutorialType, setTutorialType] = useState<'extensive' | 'brief'>(initialType)
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
      setTutorialType(initialType)
      setStep(0)
      setGradedResult(null)
    }
  }, [isOpen, initialMode, initialType])

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

  const briefSteps = [
    {
      title: 'Active Recall & Token Similarity Grading',
      badge: 'Core Recall',
      icon: '🧠',
    },
    {
      title: 'Knowledge Trees & Visual Progress Bars',
      badge: 'Structure & Progress',
      icon: '🌲',
    },
    {
      title: 'Priority Queue, Time Bank & Deep Mastery',
      badge: 'Workflow & Habits',
      icon: '⚡',
    },
  ]

  const extensiveSteps = [
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

  const steps = tutorialType === 'brief' ? briefSteps : extensiveSteps

  // Keyboard navigation (Arrow keys & Esc)
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        void finishTutorial()
      } else if (mode === 'tour') {
        if (e.key === 'ArrowRight' && step < steps.length - 1) {
          setStep((s) => s + 1)
        } else if (e.key === 'ArrowLeft' && step > 0) {
          setStep((s) => s - 1)
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, mode, step, steps.length, finishTutorial])

  if (!isOpen) return null

  // 1. Initial Welcome Prompt Mode: Choose Tutorial Depth
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
              <h2 className="text-lg font-bold text-slate-100">Choose Your Tutorial Experience</h2>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            Welcome, <strong className="text-sky-300">{user?.email ?? 'scholar'}</strong>! Your
            spaced-repetition workspace is ready. Select how thoroughly you want to tour the system:
          </p>

          <div className="grid grid-cols-1 gap-3">
            {/* Option A: Brief High-Level Tour */}
            <button
              type="button"
              onClick={() => {
                setTutorialType('brief')
                setMode('tour')
                setStep(0)
              }}
              className="group rounded-xl border border-ink-line bg-ink/70 p-4 text-left transition hover:border-sky-500/60 hover:bg-sky-950/20 cursor-pointer"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2 text-sky-300 font-bold text-xs">
                  <span>⚡</span>
                  <span>Brief High-Level Overview</span>
                </div>
                <span className="chip text-[10px] py-0.5 border-sky-500/40 text-sky-300 bg-sky-500/10 font-semibold">
                  1 min
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                A rapid 3-slide executive overview of the core architecture: Active Recall, Hierarchical Knowledge Trees with distribution bars, and the Priority Queue.
              </p>
            </button>

            {/* Option B: Extensive Deep-Dive Tour */}
            <button
              type="button"
              onClick={() => {
                setTutorialType('extensive')
                setMode('tour')
                setStep(0)
              }}
              className="group rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4 text-left transition hover:border-emerald-500/70 hover:bg-emerald-950/30 cursor-pointer"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2 text-emerald-300 font-bold text-xs">
                  <span>📘</span>
                  <span>Extensive Interactive Tutorial</span>
                </div>
                <span className="chip text-[10px] py-0.5 border-emerald-500/40 text-emerald-300 bg-emerald-500/10 font-semibold">
                  Recommended · 4 min
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Full hands-on walkthrough: test-drive the FSRS retention target slider, simulate live AI grading with the token-by-token similarity checker, explore the Knowledge Tree, and learn time-budget banking.
              </p>
            </button>
          </div>

          <div className="flex items-center justify-between pt-1 text-xs">
            <button
              type="button"
              onClick={() => void finishTutorial()}
              className="text-slate-400 hover:text-slate-200 text-xs underline underline-offset-2 transition cursor-pointer"
            >
              Skip tutorial for now
            </button>
            <span className="text-[11px] text-slate-500">
              Relaunch anytime from <strong className="text-slate-400">Start here</strong>
            </span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-2xl max-h-[92vh] rounded-2xl border border-sky-500/30 bg-[#0d131f] shadow-2xl text-slate-200 overflow-hidden">
        {/* Header with Step Info & Depth Switcher */}
        <div className="flex items-center justify-between border-b border-ink-line px-6 py-4 bg-ink-soft/40 shrink-0 gap-3">
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

          <div className="flex items-center gap-3 shrink-0">
            {/* Quick Switcher between Brief and Extensive */}
            <div className="hidden sm:flex items-center gap-1 bg-ink/80 p-0.5 rounded-lg border border-ink-line text-[11px]">
              <button
                type="button"
                onClick={() => {
                  setTutorialType('brief')
                  setStep(0)
                }}
                className={`px-2 py-0.5 rounded text-[10px] font-semibold transition cursor-pointer ${
                  tutorialType === 'brief'
                    ? 'bg-sky-500/25 text-sky-200 border border-sky-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Switch to Brief 3-slide overview"
              >
                ⚡ Brief
              </button>
              <button
                type="button"
                onClick={() => {
                  setTutorialType('extensive')
                  setStep(0)
                }}
                className={`px-2 py-0.5 rounded text-[10px] font-semibold transition cursor-pointer ${
                  tutorialType === 'extensive'
                    ? 'bg-emerald-500/25 text-emerald-200 border border-emerald-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Switch to Extensive hands-on tutorial"
              >
                📘 Extensive
              </button>
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
          {/* BRIEF TUTORIAL - STEP 0: Active Recall & AI Token Similarity */}
          {tutorialType === 'brief' && step === 0 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-2">
                <h3 className="text-sm font-bold text-sky-200 flex items-center gap-2">
                  <span>✍️</span>
                  <span>Principle 1: Active Retrieval (You Type Every Answer)</span>
                </h3>
                <p className="text-slate-300 leading-relaxed">
                  Conventional flashcard systems rely on passive recognition (flipping the card and self-grading).
                  Ars Memoriae requires <strong className="text-emerald-300">effortful active retrieval</strong>: you type your response in full,
                  activating deep neural pathways and eliminating illusory self-assessment.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-emerald-300 text-xs">
                    <span>🤖</span>
                    <span>Local AI Grading Engine</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Powered by quantized <strong className="text-slate-200">Qwen 2.5 Coder</strong> running 100% locally in Ollama.
                    It reads your typed answer and outputs structured feedback: grade, confidence, matched insights, missed nuances, and comprehensive reasoning.
                  </p>
                </div>

                <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-emerald-300 text-xs">
                    <span>🔬</span>
                    <span>Token-by-Token Similarity Checker</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    A fast local keyword and n-gram overlap heuristic runs alongside the AI grader. It cross-checks
                    semantic predictions against verbatim token matches to eliminate hallucinations and reward accurate recall.
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-ink-line bg-ink-soft/50 p-3.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 text-xs">FSRS Spaced Repetition Scheduling</span>
                  <span className="chip text-[10px] text-amber-300 border-amber-500/40">Stability & Retrievability</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Intervals are calculated using modern Free Spaced Repetition Scheduling (FSRS) based on memory stability and retrievability,
                  yielding predictable retention targets (e.g. 90%) with zero guesswork.
                </p>
              </div>
            </div>
          )}

          {/* BRIEF TUTORIAL - STEP 1: Knowledge Tree & Progress Bars */}
          {tutorialType === 'brief' && step === 1 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-2">
                <h3 className="text-sm font-bold text-sky-200 flex items-center gap-2">
                  <span>🌲</span>
                  <span>Principle 2: Hierarchical Knowledge Architecture</span>
                </h3>
                <p className="text-slate-300 leading-relaxed">
                  Knowledge is not a flat list of cards. Ars Memoriae organizes everything into a
                  <strong className="text-sky-300"> unified hierarchical Knowledge Tree</strong> with parent courses, chapters, topics, and subdecks.
                </p>
              </div>

              <div className="space-y-3">
                <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-sky-300 text-xs">
                    <span>🔀</span>
                    <span>Drag-and-Drop Study Ordering</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Drag branches directly in the Tree view to order study materials chronologically according to syllabus syllabi
                    rather than alphabetical filenames. Custom positions are saved persistently in the database.
                  </p>
                </div>

                <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-emerald-300 text-xs">
                    <span>📊</span>
                    <span>Three Real-Time Distribution Bars with Hierarchical Rollup</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed mb-2">
                    Every deck and course root displays three instant progress distribution bars:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[10px]">
                    <div className="bg-ink/80 rounded-lg p-2 border border-ink-line">
                      <span className="font-bold text-slate-300 block mb-1">👀 Cards Viewed</span>
                      <span className="text-slate-400">Unseen (0 reviews) vs New (1-2) vs Mature (3+)</span>
                    </div>
                    <div className="bg-ink/80 rounded-lg p-2 border border-ink-line">
                      <span className="font-bold text-slate-300 block mb-1">⚖️ FSRS Difficulty</span>
                      <span className="text-slate-400">Easy (&lt;4.0) vs Medium (4.0-7.0) vs Hard (&gt;7.0)</span>
                    </div>
                    <div className="bg-ink/80 rounded-lg p-2 border border-ink-line">
                      <span className="font-bold text-slate-300 block mb-1">🎯 Recall Ratings</span>
                      <span className="text-slate-400">Again, Hard, Good, and Easy response telemetry</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* BRIEF TUTORIAL - STEP 2: Priority Queue & Time Bank */}
          {tutorialType === 'brief' && step === 2 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4 space-y-2">
                <h3 className="text-sm font-bold text-emerald-200 flex items-center gap-2">
                  <span>⏱️</span>
                  <span>Principle 3: Daily Time Budgets & Deep Focus</span>
                </h3>
                <p className="text-slate-300 leading-relaxed">
                  Study fatigue is real. Ars Memoriae replaces infinite due-date backlogs with bounded daily time budgets
                  and velocity rewards.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-amber-300 text-xs">
                    <span>⏳</span>
                    <span>Priority Queue Scheduling</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Your daily session is composed from a prioritized stream of due cards, new concepts, and reading extracts.
                    Missed days smoothly distribute rather than snowballing into an 800-card wall.
                  </p>
                </div>

                <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-sky-300 text-xs">
                    <span>🏦</span>
                    <span>Time Bank Velocity Rewards</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Finishing a session under your target duration banks remaining focus minutes into your Time Bank,
                    rewarding cognitive speed and focus over passive seat time.
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-ink-line bg-ink-soft/70 p-3.5 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-purple-300 text-xs">
                  <span>💻</span>
                  <span>Interactive Code Lab & Incremental Reading</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Run automated code test suites directly in browser with a Socratic AI guide that provides progressive hints without spoiling solutions,
                  and chunk complex textbooks into bite-sized scheduled extracts with verified citations.
                </p>
              </div>

              {/* Quick Jump Action Grid */}
              <div className="pt-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                  Ready to begin? Choose your launchpad:
                </span>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => void finishTutorial('/review')}
                    className="rounded-xl border border-sky-500/40 bg-sky-950/30 p-2.5 text-center hover:bg-sky-900/40 transition group cursor-pointer"
                  >
                    <span className="text-base block mb-0.5">🎴</span>
                    <span className="font-semibold text-sky-200 text-xs block">Start Review</span>
                    <span className="text-[10px] text-slate-400">Begin active recall</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => void finishTutorial('/tree')}
                    className="rounded-xl border border-emerald-500/40 bg-emerald-950/30 p-2.5 text-center hover:bg-emerald-900/40 transition group cursor-pointer"
                  >
                    <span className="text-base block mb-0.5">🌲</span>
                    <span className="font-semibold text-emerald-200 text-xs block">Knowledge Tree</span>
                    <span className="text-[10px] text-slate-400">Explore branches</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => void finishTutorial('/decks')}
                    className="rounded-xl border border-purple-500/40 bg-purple-950/30 p-2.5 text-center hover:bg-purple-900/40 transition group cursor-pointer"
                  >
                    <span className="text-base block mb-0.5">📁</span>
                    <span className="font-semibold text-purple-200 text-xs block">Decks & Cards</span>
                    <span className="text-[10px] text-slate-400">Import or create</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* EXTENSIVE TUTORIAL - STEP 0: FSRS & Active Recall */}
          {tutorialType === 'extensive' && step === 0 && (
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

          {/* EXTENSIVE TUTORIAL - STEP 1: Live AI Grading Simulator */}
          {tutorialType === 'extensive' && step === 1 && (
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

          {/* EXTENSIVE TUTORIAL - STEP 2: Knowledge Tree */}
          {tutorialType === 'extensive' && step === 2 && (
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

          {/* EXTENSIVE TUTORIAL - STEP 3: Priority Queue & Time Bank */}
          {tutorialType === 'extensive' && step === 3 && (
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

          {/* EXTENSIVE TUTORIAL - STEP 4: Incremental Reading & Code Lab */}
          {tutorialType === 'extensive' && step === 4 && (
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

          {/* EXTENSIVE TUTORIAL - STEP 5: Ready to Begin! */}
          {tutorialType === 'extensive' && step === 5 && (
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
