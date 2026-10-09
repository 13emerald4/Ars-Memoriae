import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Bank, LearningAnalytics, Stats } from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

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
    title: 'Turn on local AI grading',
    body: 'Optional. Start Ollama (ollama run qwen2.5-coder:7b), then turn on LLM grading in Settings. It unlocks grading with reasoning, Learn & Practice lessons, and the Socratic Guide. Without it, the app still functions completely via manual grading.',
    route: '/settings',
    routeLabel: 'Go to Settings',
    done: (c) => c.llmEnabled,
    optional: true,
  },
  {
    title: 'Create or import your first cards',
    body: 'Add a deck and write notes by hand, or bulk-import JSON notes.',
    route: '/decks',
    routeLabel: 'Go to Decks',
    done: (c) => c.cardCount > 0,
  },
  {
    title: 'Add reading material or upload a document',
    body: 'Paste an article URL, text, or upload a document. It splits into paragraph extracts with verified citations (page numbers/sections) that schedule into your queue.',
    route: '/read',
    routeLabel: 'Go to Read',
    done: (c) => c.sourcesActive > 0,
    optional: true,
  },
  {
    title: 'Review with Active Recall & Metacognitive Confidence',
    body: 'Select your pre-recall confidence level (Judgment of Learning: Guess, Unsure, Likely, Solid), type your answer, and review the LLM grade breakdown or self-grade.',
    route: '/review',
    routeLabel: 'Go to Review',
    done: (c) => c.reviewsLogged > 0,
  },
  {
    title: 'Run a timed study block in the Time Bank',
    body: 'Start a focused block with a duration and card target on the Review page. Finishing early banks remaining time to reward mastery velocity over passive seat time.',
    route: '/review',
    routeLabel: 'Go to Review',
    done: (c) => c.blocksFinished > 0,
  },
  {
    title: 'Post-session reflection',
    body: 'Answer what distracted you and your plan for the next block — closing the executive-function loop after hitting your study goal.',
    route: '/review',
    routeLabel: 'Go to Review',
    done: (c) => c.hasReflected,
    optional: true,
  },
  {
    title: 'Inspect your Learning Sciences Analytics',
    body: 'Examine your cognitive fatigue horizon, 24-hour chronotype efficiency map, psychometric item discrimination (r_pb), desirable difficulty yield, and Brier calibration.',
    route: '/stats',
    routeLabel: 'Go to Stats',
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
    title: 'Learning Sciences Analytics Suite',
    body: 'View your optimal focus breakpoint (e.g. 25 min), peak circadian study window, ambiguous card triage (negative r_pb correlation), and Brier calibration curve.',
    route: '/stats',
    routeLabel: 'Go to Stats',
    tag: 'Analytics',
  },
  {
    title: 'Knowledge Tree & Prerequisite Gating',
    body: 'Organize topics, decks, and sources in a SuperMemo-style unified hierarchy. Set prerequisite gates governed by EWMA health meters and Wald’s SPRT sequential hypothesis tests.',
    route: '/tree',
    routeLabel: 'Go to Tree',
    tag: 'Structure',
  },
  {
    title: 'Learn & Practice Mode',
    body: 'Read an AI-synthesized micro-lesson built directly from verified document citations before being tested on a card.',
    route: '/review',
    routeLabel: 'Go to Review',
    tag: 'Study Mode',
  },
  {
    title: 'Socratic AI Guide',
    body: 'Stuck on a challenging card? The Socratic Guide asks focused diagnostic questions to lead you to the answer without spoiling it.',
    route: '/review',
    routeLabel: 'Go to Review',
    tag: 'Tutoring',
  },
  {
    title: 'Confusable Card & Interference Scan',
    body: 'Automatically detect sister cards with high prompt similarity but different answers (Mnemosyne principle). The review queue spaces them apart to prevent proactive interference.',
    route: '/stats',
    routeLabel: 'Go to Stats',
    tag: 'Interference',
  },
  {
    title: 'Leech Triage & Auto-Remediation',
    body: 'Cards crossing the lapse threshold are diagnosed by the LLM with proposals to rewrite, split into atomic facts, or clarify ambiguous phrasing.',
    route: '/stats',
    routeLabel: 'Go to Stats',
    tag: 'Remediation',
  },
  {
    title: 'Image Occlusion Studio',
    body: 'Upload anatomical or technical diagrams, drag rectangular masks, and generate occlusion cards that highlight the target while masking surrounding labels.',
    route: '/decks',
    routeLabel: 'Go to Decks',
    tag: 'Visual',
  },
  {
    title: 'Settings: FSRS & Backlog Smoothing',
    body: 'Configure target retention (85–90%), review time budgets, interval fuzzing (±5%), and backlog smoothing to prevent missed days from creating walls of reviews.',
    route: '/settings',
    routeLabel: 'Go to Settings',
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
                {done ? '✓' : i + 1}
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
    </div>
  )
}
