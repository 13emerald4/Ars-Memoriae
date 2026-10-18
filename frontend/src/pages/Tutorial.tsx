import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Bank, LearningAnalytics, Stats } from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import InteractiveTutorialModal from '../components/InteractiveTutorialModal'

/** Getting Started Tutorial: the app's features in pedagogical order.
 *
 *  Progress is computed directly from verified database telemetry rather than
 *  self-reported checkboxes — keeping tutorial progression as rigorous and
 *  honest as the Time Bank and mastery analytics.
 */

interface Milestone {
  title: string
  body: string
  route: string
  routeLabel: string
  done: (ctx: Ctx) => boolean
  optional?: boolean
}

interface Ctx {
  llmEnabled: boolean
  cardCount: number
  sourcesActive: number
  reviewsLogged: number
  blocksFinished: number
  hasReflected: boolean
  hasAnalytics: boolean
  hasGatedNode: boolean
}

const MILESTONES: Milestone[] = [
  {
    title: 'Enable AI grading',
    body: 'Optional. Turn on LLM grading in Settings for automated feedback and reasoning.',
    route: '/settings',
    routeLabel: 'Settings',
    done: (c) => c.llmEnabled,
    optional: true,
  },
  {
    title: 'Create or import cards',
    body: 'Add a deck and create cards, or import JSON.',
    route: '/decks',
    routeLabel: 'Decks',
    done: (c) => c.cardCount > 0,
  },
  {
    title: 'Add reading material',
    body: 'Import text or documents to schedule extracts into your queue.',
    route: '/read',
    routeLabel: 'Read',
    done: (c) => c.sourcesActive > 0,
    optional: true,
  },
  {
    title: 'Active recall review',
    body: 'Select confidence, type your answer, and review AI grading. Conceptual mistakes are saved to memory to coach you on future reviews.',
    route: '/review',
    routeLabel: 'Review',
    done: (c) => c.reviewsLogged > 0,
  },
  {
    title: 'Timed study block',
    body: 'Set a duration and card target. Finish early to bank time.',
    route: '/review',
    routeLabel: 'Review',
    done: (c) => c.blocksFinished > 0,
  },
  {
    title: 'Session reflection',
    body: 'Log distractions and action plans after completing a block.',
    route: '/review',
    routeLabel: 'Review',
    done: (c) => c.hasReflected,
    optional: true,
  },
  {
    title: 'Learning analytics',
    body: 'View fatigue, chronotype efficiency, difficulty, and calibration.',
    route: '/stats',
    routeLabel: 'Stats',
    done: (c) => c.hasAnalytics,
  },
]

interface Extra {
  title: string
  body: string
  route: string
  routeLabel: string
  tag?: string
}

const EXPLORE_WHEN_READY: Extra[] = [
  {
    title: 'Learning Analytics',
    body: 'Optimal focus breakpoint, chronotype efficiency, ambiguous card triage, and calibration.',
    route: '/stats',
    routeLabel: 'Stats',
    tag: 'Analytics',
  },
  {
    title: 'Knowledge Tree',
    body: 'Organize topics, decks, and sources in a hierarchy with prerequisite gating.',
    route: '/tree',
    routeLabel: 'Tree',
    tag: 'Structure',
  },
  {
    title: 'Learn & Practice',
    body: 'Micro-lessons built from source citations before testing each card.',
    route: '/review',
    routeLabel: 'Review',
    tag: 'Study Mode',
  },
  {
    title: 'Socratic Guide',
    body: 'Diagnostic questions to guide you to the answer without spoiling it.',
    route: '/review',
    routeLabel: 'Review',
    tag: 'Tutoring',
  },
  {
    title: 'Past Mistake Memory',
    body: 'Remembers your specific misconceptions across reviews and offers diagnostic hints before you answer.',
    route: '/review',
    routeLabel: 'Review',
    tag: 'Memory',
  },
  {
    title: 'Interference Scan',
    body: 'Detect sister cards with similar prompts to prevent confusion.',
    route: '/stats',
    routeLabel: 'Stats',
    tag: 'Interference',
  },
  {
    title: 'Leech Triage',
    body: 'Diagnose and remediate cards with repeated lapses.',
    route: '/stats',
    routeLabel: 'Stats',
    tag: 'Remediation',
  },
  {
    title: 'Image Occlusion',
    body: 'Mask regions of diagrams to generate visual recall cards.',
    route: '/decks',
    routeLabel: 'Decks',
    tag: 'Visual',
  },
  {
    title: 'Settings & FSRS',
    body: 'Configure retention targets, daily budgets, and backlog smoothing.',
    route: '/settings',
    routeLabel: 'Settings',
    tag: 'Configuration',
  },
]

export default function Tutorial() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState<Stats | null>(null)
  const [analytics, setAnalytics] = useState<LearningAnalytics | null>(null)
  const [bank, setBank] = useState<Bank | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [showInteractiveTour, setShowInteractiveTour] = useState(false)
  const [tourType, setTourType] = useState<'extensive' | 'brief'>('extensive')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, a, b] = await Promise.all([
        api.stats(),
        api.learningAnalytics().catch(() => null),
        api.bank().catch(() => null),
      ])
      setStats(s)
      setAnalytics(a)
      setBank(b)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading || !user) return <Spinner label="Checking your progress…" />

  const ctx: Ctx = {
    llmEnabled: user.llm_grading_consent,
    cardCount: stats?.totals.cards ?? 0,
    sourcesActive: stats?.ir_throughput.sources_active ?? 0,
    reviewsLogged: stats?.totals.reviews_logged ?? 0,
    blocksFinished: bank?.recent.length ?? 0,
    hasReflected: bank?.recent.some((s) => s.distraction || s.next_time_plan) ?? false,
    hasAnalytics: Boolean(analytics && (analytics.fatigue.curve.length > 0 || ctx_hasReviews(stats))),
    hasGatedNode: Boolean(analytics && analytics.sprt_gating.length > 0),
  }

  function ctx_hasReviews(s: Stats | null): boolean {
    return (s?.totals.reviews_logged ?? 0) > 0
  }

  const required = MILESTONES.filter((m) => !m.optional)
  const requiredDone = required.filter((m) => m.done(ctx)).length

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />

      {/* Interactive Walkthrough Banner */}
      <div className="card border-sky-500/40 bg-gradient-to-r from-sky-950/40 via-ink-soft to-ink-soft p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-sky-200">Interactive Walkthrough</h2>
            <span className="chip border-sky-500/40 text-sky-300 text-[10px] font-semibold">Self-Paced</span>
          </div>
          <p className="mt-1 text-xs text-slate-400 max-w-xl">
            Choose between an interactive simulation or a brief overview.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => {
              setTourType('brief')
              setShowInteractiveTour(true)
            }}
            className="btn text-xs font-semibold px-3.5 py-2 border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-200"
          >
            Brief (1 min)
          </button>
          <button
            type="button"
            onClick={() => {
              setTourType('extensive')
              setShowInteractiveTour(true)
            }}
            className="btn btn-primary text-xs font-semibold px-4 py-2 shadow-lg shadow-sky-500/10"
          >
            Full Tutorial (4 min) →
          </button>
        </div>
      </div>

      <InteractiveTutorialModal
        isOpen={showInteractiveTour}
        onClose={() => setShowInteractiveTour(false)}
        initialMode="tour"
        initialType={tourType}
      />

      <Section
        title="Getting started"
        description="The core spaced-repetition and knowledge mastery workflow. Progress is measured from real learning telemetry."
      >
        <div className="flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-line">
            <div
              className="h-full rounded-full bg-emerald-400/70 transition-all"
              style={{ width: `${(requiredDone / required.length) * 100}%` }}
            />
          </div>
          <span className="whitespace-nowrap text-xs tabular-nums text-slate-500">
            {requiredDone}/{required.length} core milestones completed
          </span>
        </div>
      </Section>

      <div className="space-y-3">
        {MILESTONES.map((m, i) => {
          const done = m.done(ctx)
          return (
            <div
              key={m.title}
              className={`card flex items-start gap-4 transition-all ${
                done ? 'border-emerald-500/20 bg-emerald-950/10 opacity-80' : 'border-ink-line'
              }`}
            >
              <div
                className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  done
                    ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40'
                    : 'border border-ink-line text-slate-500'
                }`}
              >
                {done ? (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className={`text-sm font-medium ${done ? 'text-emerald-200' : 'text-slate-200'}`}>
                    {m.title}
                  </h3>
                  {m.optional && (
                    <span className="chip text-slate-600" title="Skippable — the app works without it">
                      optional
                    </span>
                  )}
                  {done && <span className="chip border-emerald-500/40 text-emerald-300">completed</span>}
                </div>
                <p className="mt-1 text-xs text-slate-400">{m.body}</p>
                {!done && (
                  <button className="btn mt-3 px-2.5 py-1 text-xs" onClick={() => navigate(m.route)}>
                    {m.routeLabel}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <Section
        title="Explore when you're ready"
        description="Advanced cognitive architectures, diagnostic tools, and custom configurations."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {EXPLORE_WHEN_READY.map((x) => (
            <div key={x.title} className="rounded-lg border border-ink-line bg-ink/60 p-4 transition-all hover:border-slate-700">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-medium text-slate-200">{x.title}</h3>
                {x.tag && <span className="chip text-[10px] text-slate-500">{x.tag}</span>}
              </div>
              <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">{x.body}</p>
              <button className="btn mt-3 px-2.5 py-1 text-xs" onClick={() => navigate(x.route)}>
                {x.routeLabel}
              </button>
            </div>
          ))}
        </div>
      </Section>

      {/* Feature Request & Feedback Callout */}
      <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-sky-400 font-semibold text-sm">Have a feature request or feedback?</span>
            <span className="chip text-[10px] border-sky-500/40 text-sky-300">Feedback</span>
          </div>
          <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
            Ars Memoriae is actively developed! You can submit ideas, suggest adjustments, or request new features anytime directly from <strong className="text-slate-100">Settings → Feature Requests & Feedback</strong>.
          </p>
        </div>
        <button
          onClick={() => navigate('/settings')}
          className="btn btn-secondary text-xs font-semibold px-3.5 py-1.5 shrink-0 flex items-center gap-1.5 cursor-pointer"
        >
          <span>Feature Requests</span>
          <span>→</span>
        </button>
      </div>
    </div>
  )
}
