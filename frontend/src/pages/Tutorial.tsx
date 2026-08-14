import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Bank, Stats } from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

/** Getting Started: the app's features, in the order they're meant to be
 *  reached for.
 *
 *  Progress here is read off real usage, not a self-reported checklist — the
 *  same principle the Time Bank is built on (session_service.py: "work is
 *  counted server-side... a bank you can inflate by editing a request body
 *  measures nothing"). A tutorial that just asks "did you do this?" and
 *  trusts a checkbox is exactly that kind of number.
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
  hasApiKey: boolean
  cardCount: number
  sourcesActive: number
  reviewsLogged: number
  blocksFinished: number
  hasReflected: boolean
}

const MILESTONES: Milestone[] = [
  {
    title: 'Add your Google API key',
    body: 'Optional, but it unlocks LLM grading, Learn & Practice lessons, and the Socratic Guide. Without it the app still works end to end — grading falls back to four manual buttons.',
    route: '/settings',
    routeLabel: 'Go to Settings',
    done: (c) => c.hasApiKey,
    optional: true,
  },
  {
    title: 'Create or import your first cards',
    body: 'Add a deck and type a note by hand, import an Anki .apkg (review history replays through FSRS so nothing is lost), or bulk-import from JSON.',
    route: '/decks',
    routeLabel: 'Go to Decks',
    done: (c) => c.cardCount > 0,
  },
  {
    title: 'Add something to read',
    body: 'Paste text, a URL, or upload a document. It splits into extracts that resurface on a schedule, and you can generate cards from it that cite the passage they came from.',
    route: '/read',
    routeLabel: 'Go to Read',
    done: (c) => c.sourcesActive > 0,
    optional: true,
  },
  {
    title: 'Review your first card',
    body: "Type an answer, get graded with reasoning shown, then confirm (or override) the grade — that's what FSRS actually schedules on.",
    route: '/review',
    routeLabel: 'Go to Review',
    done: (c) => c.reviewsLogged > 0,
  },
  {
    title: 'Run a timed study block',
    body: 'Start a block with a duration and a card target from the Review page. Whatever time you don’t spend once you hit the target is banked as earned free time.',
    route: '/review',
    routeLabel: 'Go to Review',
    done: (c) => c.blocksFinished > 0,
  },
  {
    title: 'Reflect when a block ends',
    body: 'What distracted you, and how will you fix it next time? Two optional questions after a block closes — the exit half of the focus-goal prompt you set going in.',
    route: '/review',
    routeLabel: 'Go to Review',
    done: (c) => c.hasReflected,
    optional: true,
  },
]

interface Extra {
  title: string
  body: string
  route: string
  routeLabel: string
}

const EXPLORE_WHEN_READY: Extra[] = [
  {
    title: 'Knowledge tree',
    body: 'One hierarchy over every deck and article. Set priority down a whole branch at once, or gate one branch behind mastering another.',
    route: '/tree',
    routeLabel: 'Go to Tree',
  },
  {
    title: 'Learn & Practice',
    body: "Toggle it on in Review to read a short lesson built from a card's citations before you're asked the question — useful right after adding cards from something you haven't read closely yet.",
    route: '/review',
    routeLabel: 'Go to Review',
  },
  {
    title: 'Ask your Guide',
    body: 'Stuck on a card before revealing the answer? The Guide asks one diagnostic question at a time and is built to never just hand you the answer.',
    route: '/review',
    routeLabel: 'Go to Review',
  },
  {
    title: 'Stats',
    body: 'Activity heatmap, retention by interval, mastery velocity, and leeches (cards you keep failing) with model-proposed fixes — rewrite, split, or suspend.',
    route: '/stats',
    routeLabel: 'Go to Stats',
  },
  {
    title: 'Settings: scheduling & load',
    body: 'Desired retention, daily new/review caps, backlog smoothing, and the queue mix between due reviews, new cards, and reading.',
    route: '/settings',
    routeLabel: 'Go to Settings',
  },
]

export default function Tutorial() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState<Stats | null>(null)
  const [bank, setBank] = useState<Bank | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, b] = await Promise.all([api.stats(), api.bank()])
      setStats(s)
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
    hasApiKey: user.has_api_key,
    cardCount: stats?.totals.cards ?? 0,
    sourcesActive: stats?.ir_throughput.sources_active ?? 0,
    reviewsLogged: stats?.totals.reviews_logged ?? 0,
    blocksFinished: bank?.recent.length ?? 0,
    hasReflected: bank?.recent.some((s) => s.distraction || s.next_time_plan) ?? false,
  }

  const required = MILESTONES.filter((m) => !m.optional)
  const requiredDone = required.filter((m) => m.done(ctx)).length

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />

      <Section
        title="Getting started"
        description="The features, in the order they build on each other. Progress below reflects what you've actually done, not a checkbox."
      >
        <div className="flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-line">
            <div
              className="h-full rounded-full bg-emerald-400/70 transition-all"
              style={{ width: `${(requiredDone / required.length) * 100}%` }}
            />
          </div>
          <span className="whitespace-nowrap text-xs tabular-nums text-slate-500">
            {requiredDone}/{required.length} core steps
          </span>
        </div>
      </Section>

      <div className="space-y-3">
        {MILESTONES.map((m, i) => {
          const done = m.done(ctx)
          return (
            <div
              key={m.title}
              className={`card flex items-start gap-4 ${done ? 'opacity-70' : ''}`}
            >
              <div
                className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  done
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'border border-ink-line text-slate-500'
                }`}
              >
                {done ? '✓' : i + 1}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-medium text-slate-200">{m.title}</h3>
                  {m.optional && (
                    <span className="chip text-slate-600" title="Skippable — the app works without it">
                      optional
                    </span>
                  )}
                  {done && <span className="chip border-emerald-500/40 text-emerald-300">done</span>}
                </div>
                <p className="mt-1 text-xs text-slate-500">{m.body}</p>
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
        description="Not a sequence — dip into these whenever they're useful."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {EXPLORE_WHEN_READY.map((x) => (
            <div key={x.title} className="rounded-lg border border-ink-line p-4">
              <h3 className="text-sm font-medium text-slate-200">{x.title}</h3>
              <p className="mt-1 text-xs text-slate-500">{x.body}</p>
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
