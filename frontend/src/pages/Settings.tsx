import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { EventReadiness, QueueConfig, User } from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import { FullscreenButton, useFullscreen } from '../components/FullscreenContext'



export default function Settings() {
  const { user, refresh, signOut } = useAuth()
  const [queueCfg, setQueueCfg] = useState<QueueConfig | null>(null)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    try {
      setQueueCfg(await api.queueConfig())
    } catch (err) {
      setError(err)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (!user || !queueCfg) return <Spinner />

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />
      <QwenCoderPanel user={user} onChange={refresh} />
      <MemoryChampionPanel user={user} onChange={refresh} />
      <DisplayFocusPanel />
      <SchedulingPanel user={user} onChange={refresh} />
      <QueuePanel cfg={queueCfg} onChange={load} />
      <DataPanel user={user} />

      <Section title="Account" description={user.email}>
        <button className="btn btn-danger" onClick={signOut}>
          Sign out
        </button>
      </Section>
    </div>
  )
}

function QwenCoderPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [status, setStatus] = useState<{
    connected: boolean
    provider: string
    base_url: string
    model: string
    models_installed: string[]
    model_ready: boolean
    error?: string | null
  } | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const checkStatus = useCallback(async () => {
    setChecking(true)
    setError(null)
    try {
      const s = await api.llmStatus()
      setStatus(s)
    } catch (err) {
      setError(err)
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    void checkStatus()
  }, [checkStatus])

  return (
    <Section
      title="💻 Local AI Engine (Qwen 2.5 Coder 7B Instruct)"
      description="Zero cloud costs, zero rate limits, and 100% private. Runs on your machine via Ollama."
    >
      <div className="space-y-6">
        {/* Connection status card */}
        <div className="rounded-xl border border-ink-line bg-ink/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span
                className={`flex h-3 w-3 rounded-full ${
                  status?.connected && status?.model_ready
                    ? 'bg-emerald-400 ring-4 ring-emerald-500/20 animate-pulse'
                    : status?.connected
                    ? 'bg-amber-400 ring-4 ring-amber-500/20'
                    : 'bg-rose-500 ring-4 ring-rose-500/20'
                }`}
              />
              <div>
                <h4 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <span>Qwen 2.5 Coder 7B Instruct</span>
                  <span className="chip text-[10px] px-1.5 py-0.2 border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
                    Active Grader
                  </span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Endpoint: <code className="font-mono text-slate-300">{status?.base_url || 'http://localhost:11434'}</code>
                </p>
              </div>
            </div>

            <button
              className="btn text-xs py-1.5 px-3"
              disabled={checking}
              onClick={() => void checkStatus()}
            >
              {checking ? 'Testing…' : '↻ Test Connection'}
            </button>
          </div>

          {/* Status Diagnostic Callout */}
          {status && (
            <div className="mt-4 pt-3 border-t border-ink-line text-xs">
              {status.connected && status.model_ready ? (
                <div className="flex items-center gap-2 text-emerald-300">
                  <span>✓</span>
                  <span>Ollama is online and <strong>qwen2.5-coder:7b</strong> is ready to grade solutions.</span>
                </div>
              ) : status.connected ? (
                <div className="space-y-2">
                  <p className="text-amber-300 font-medium">
                    ⚠️ Ollama is running, but model <strong>qwen2.5-coder:7b</strong> was not detected in your local library.
                  </p>
                  <p className="text-slate-400">
                    Run this command in your PowerShell / Terminal to download it:
                  </p>
                  <pre className="rounded bg-black/40 p-2 font-mono text-amber-200 text-xs select-all">
                    ollama run qwen2.5-coder:7b
                  </pre>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-rose-300 font-medium">
                    🔴 Could not connect to Ollama at <code className="font-mono">{status.base_url}</code>.
                  </p>
                  <p className="text-slate-400">
                    Make sure Ollama is installed and running on your computer. Start it with:
                  </p>
                  <pre className="rounded bg-black/40 p-2 font-mono text-sky-200 text-xs select-all">
                    ollama run qwen2.5-coder:7b
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Feature Toggles */}
        <div className="space-y-3 rounded-lg border border-ink-line bg-ink/40 p-4">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={user.llm_grading_consent}
              className="mt-1"
              onChange={async (e) => {
                await api.updateMe({ llm_grading_consent: e.target.checked })
                await onChange()
              }}
            />
            <span className="text-sm">
              <span className="font-medium text-slate-200">Enable local AI solution grading</span>
              <span className="mt-0.5 block text-xs text-slate-400">
                Grades code correctness, Big-O asymptotic efficiency, and logic edge cases locally using Qwen 2.5 Coder.
              </span>
            </span>
          </label>

          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={user.leech_remediation_opt_in}
              className="mt-1"
              onChange={async (e) => {
                await api.updateMe({ leech_remediation_opt_in: e.target.checked })
                await onChange()
              }}
            />
            <span className="text-sm">
              <span className="font-medium text-slate-200">Automatic Leech card remediation diagnosis</span>
              <span className="mt-0.5 block text-xs text-slate-400">
                When you repeatedly struggle with a card, Qwen analyzes your errors and proposes clearer reformulated cards.
              </span>
            </span>
          </label>
        </div>

        <ErrorNote error={error} />
      </div>
    </Section>
  )
}

function MemoryChampionPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [readiness, setReadiness] = useState<EventReadiness | null>(null)
  const [loadingReadiness, setLoadingReadiness] = useState(false)

  const save = async (patch: Partial<User>) => {
    await api.updateMe(patch)
    await onChange()
    void fetchReadiness()
  }

  const fetchReadiness = useCallback(() => {
    setLoadingReadiness(true)
    api
      .eventReadiness()
      .then(setReadiness)
      .catch(() => setReadiness(null))
      .finally(() => setLoadingReadiness(false))
  }, [])

  useEffect(() => {
    fetchReadiness()
  }, [fetchReadiness, user.target_event_date])

  const thresholdSec = ((user.automaticity_threshold_ms ?? 3000) / 1000).toFixed(1)
  const eventDateStr = user.target_event_date
    ? new Date(user.target_event_date).toISOString().slice(0, 10)
    : ''

  return (
    <Section
      title="🧠 Memory Champion & Athlete Settings"
      description="Competitive memory athlete protocols: reaction latency automaticity tracking and Event Horizon peak-performance taper scheduling."
    >
      <div className="space-y-6">
        {/* Automaticity Latency Threshold (§Feature 4) */}
        <div>
          <Field
            label={`Automaticity Reaction Threshold (${thresholdSec}s)`}
            hint="Target response pace for reflex automaticity telemetry. Informational only — your FSRS review grade and schedule are determined strictly by answer correctness."
          >
            <div className="flex items-center gap-4 mt-2">
              <input
                type="range"
                min={500}
                max={10000}
                step={250}
                defaultValue={user.automaticity_threshold_ms ?? 3000}
                className="flex-1"
                onMouseUp={(e) =>
                  save({ automaticity_threshold_ms: Number((e.target as HTMLInputElement).value) })
                }
              />
              <span className="w-16 font-mono text-sm font-semibold text-amber-300 text-right">
                {thresholdSec}s
              </span>
            </div>
          </Field>
        </div>

        {/* Event Horizon Peak Taper (§Feature 6) */}
        <div className="border-t border-ink-line pt-4 space-y-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            🎯 Target Event Horizon (Competition / Exam Taper)
          </p>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Event Title" hint="e.g. Memory Championship, USMLE, Bar Exam">
              <input
                type="text"
                className="input"
                defaultValue={user.target_event_title ?? ''}
                placeholder="Target Competition / Exam"
                onBlur={(e) => save({ target_event_title: e.target.value.trim() || null })}
              />
            </Field>

            <Field label="Target Event Date" hint="When intervals compress for peak recall">
              <input
                type="date"
                className="input"
                defaultValue={eventDateStr}
                onChange={(e) => {
                  const val = e.target.value
                  save({ target_event_date: val ? new Date(val).toISOString() : null })
                }}
              />
            </Field>

            <Field label="Peak Retention Target" hint="Target retention on event day (e.g. 0.95)">
              <input
                type="number"
                step={0.01}
                min={0.7}
                max={0.99}
                className="input"
                defaultValue={user.peak_retention_target ?? 0.95}
                onBlur={(e) => save({ peak_retention_target: Number(e.target.value) })}
              />
            </Field>
          </div>

          {/* Live Event Readiness Telemetry Card */}
          {loadingReadiness ? (
            <p className="text-xs text-slate-500 italic">Calculating event readiness telemetry…</p>
          ) : readiness?.is_active ? (
            <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-bold text-sky-200 uppercase tracking-wide">
                    {readiness.target_event_title || 'Active Target Event'}
                  </span>
                </div>
                <span className="chip border-sky-500/40 text-sky-300 font-semibold">
                  {readiness.status_label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[10px] text-slate-400">Countdown</p>
                  <p className="font-mono text-xl font-bold text-amber-300">
                    {readiness.days_remaining}d
                  </p>
                  <p className="text-[9px] text-slate-500">until event</p>
                </div>

                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[10px] text-slate-400">Projected Retention</p>
                  <p className="font-mono text-xl font-bold text-emerald-400">
                    {Math.round(readiness.projected_retention * 100)}%
                  </p>
                  <p className="text-[9px] text-slate-500">at event horizon</p>
                </div>

                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[10px] text-slate-400">Unstable Cards</p>
                  <p className="font-mono text-xl font-bold text-rose-300">
                    {readiness.unstable_cards_count}
                  </p>
                  <p className="text-[9px] text-slate-500">stability &lt; 7d</p>
                </div>

                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[10px] text-slate-400">Required Pace</p>
                  <p className="font-mono text-xl font-bold text-sky-300">
                    ~{readiness.estimated_daily_reviews_needed}
                  </p>
                  <p className="text-[9px] text-slate-500">reviews / day</p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </Section>
  )
}

function SchedulingPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [optimizeMsg, setOptimizeMsg] = useState<string | null>(null)

  const save = async (patch: Partial<User>) => {
    await api.updateMe(patch)
    await onChange()
  }

  return (
    <Section
      title="Scheduling & load"
      description="FSRS targets a retention rate rather than a fixed interval table. The caps below are what stop a missed week from turning into an 800-card wall."
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Desired retention" hint="0.90 = you want to recall 90% of due cards.">
          <input
            type="number"
            step={0.01}
            min={0.7}
            max={0.99}
            className="input"
            defaultValue={user.desired_retention}
            onBlur={(e) => save({ desired_retention: Number(e.target.value) })}
          />
        </Field>
        <Field label="Session budget (minutes)" hint="The queue fills this, rather than dumping a list.">
          <input
            type="number"
            min={1}
            max={600}
            className="input"
            defaultValue={user.queue_time_budget_minutes}
            onBlur={(e) => save({ queue_time_budget_minutes: Number(e.target.value) })}
          />
        </Field>
        <Field label="New cards / day">
          <input
            type="number"
            min={0}
            className="input"
            defaultValue={user.daily_new_limit}
            onBlur={(e) => save({ daily_new_limit: Number(e.target.value) })}
          />
        </Field>
        <Field label="Max reviews / day">
          <input
            type="number"
            min={0}
            className="input"
            defaultValue={user.daily_review_limit}
            onBlur={(e) => save({ daily_review_limit: Number(e.target.value) })}
          />
        </Field>
        <Field label="Spread a backlog over (days)" hint="Missed days get smoothed across this window.">
          <input
            type="number"
            min={1}
            max={60}
            className="input"
            defaultValue={user.backlog_spread_days}
            onBlur={(e) => save({ backlog_spread_days: Number(e.target.value) })}
          />
        </Field>
        <Field label="Leech threshold (lapses)">
          <input
            type="number"
            min={2}
            max={100}
            className="input"
            defaultValue={user.leech_threshold}
            onBlur={(e) => save({ leech_threshold: Number(e.target.value) })}
          />
        </Field>
      </div>

      <div className="mt-5 border-t border-ink-line pt-4">
        <p className="text-xs text-slate-500">
          FSRS parameters:{' '}
          {user.fsrs_optimized_at
            ? `personalized ${new Date(user.fsrs_optimized_at).toLocaleDateString()}`
            : 'using defaults until you have enough review history'}
        </p>
        <button
          className="btn mt-2"
          onClick={async () => {
            const r = await api.optimize()
            setOptimizeMsg(
              r.optimized
                ? 'Parameters refit from your review history.'
                : (r.reason ?? 'Not enough history yet.'),
            )
            await onChange()
          }}
        >
          Refit parameters now
        </button>
        {optimizeMsg && <p className="mt-2 text-xs text-slate-400">{optimizeMsg}</p>}
      </div>
    </Section>
  )
}

function QueuePanel({ cfg, onChange }: { cfg: QueueConfig; onChange: () => Promise<void> }) {
  const save = async (patch: Partial<QueueConfig>) => {
    await api.updateQueueConfig(patch)
    await onChange()
  }
  const total = cfg.review_weight + cfg.new_weight + cfg.ir_weight || 1

  return (
    <Section
      title="Queue mix"
      description="How the session budget is split between due reviews, new cards, and reading. Ship-with-conservative-defaults; tune from real use."
    >
      <div className="space-y-4">
        {(
          [
            ['review_weight', 'Due reviews'],
            ['new_weight', 'New cards'],
            ['ir_weight', 'Reading'],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-4 text-sm">
            <span className="w-28 text-slate-400">{label}</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              defaultValue={cfg[key]}
              className="flex-1"
              onMouseUp={(e) => save({ [key]: Number((e.target as HTMLInputElement).value) })}
            />
            <span className="w-12 text-right text-xs tabular-nums text-slate-500">
              {Math.round((cfg[key] / total) * 100)}%
            </span>
          </label>
        ))}

        <div className="grid gap-4 border-t border-ink-line pt-4 sm:grid-cols-2">
          <Field label="Seconds per review" hint="Auto-refined from your real timings after 30 reviews.">
            <input
              type="number"
              min={1}
              className="input"
              defaultValue={cfg.seconds_per_review}
              onBlur={(e) => save({ seconds_per_review: Number(e.target.value) })}
            />
          </Field>
          <Field label="Seconds per extract">
            <input
              type="number"
              min={1}
              className="input"
              defaultValue={cfg.seconds_per_ir_extract}
              onBlur={(e) => save({ seconds_per_ir_extract: Number(e.target.value) })}
            />
          </Field>
        </div>
      </div>
    </Section>
  )
}

function DataPanel({ user }: { user: User }) {
  const [busy, setBusy] = useState(false)
  return (
    <Section
      title="Your data"
      description="Full-fidelity export, on demand, hosted or self-hosted. No lock-in mechanism exists here."
    >
      <div className="flex flex-wrap gap-2">
        <button
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.downloadExport('/api/export', 'memorization-export.json')
            } finally {
              setBusy(false)
            }
          }}
        >
          Download full export (JSON)
        </button>
        <button
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.downloadExport('/api/export/review-logs.csv', 'review-logs.csv')
            } finally {
              setBusy(false)
            }
          }}
        >
          Download review logs (CSV)
        </button>
      </div>
      <p className="mt-3 text-xs text-slate-600">
        The export contains decks, notes, cards with live FSRS state, every review log, and your
        reading sources. Your API key is deliberately excluded.
        {user.has_api_key ? '' : ''}
      </p>
    </Section>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div>
      <p className="label">{label}</p>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-600">{hint}</p>}
    </div>
  )
}

function DisplayFocusPanel() {
  const { isZenMode, toggleZenMode } = useFullscreen()

  return (
    <Section
      title="Display & Fullscreen Focus Mode"
      description="Configure immersive, distraction-free study sessions and keyboard shortcuts."
    >
      <div className="flex flex-wrap items-center gap-4">
        <FullscreenButton />
        <button
          type="button"
          onClick={toggleZenMode}
          className={`btn ${isZenMode ? 'btn-primary' : 'btn-secondary'}`}
        >
          {isZenMode ? '✓ Zen Distraction-Free Active' : 'Enable Zen Distraction-Free'}
        </button>
      </div>

      <div className="mt-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-3.5 space-y-2 text-xs">
        <p className="font-semibold text-slate-300">Keyboard Shortcuts:</p>
        <ul className="space-y-1.5 text-slate-400">
          <li className="flex items-center gap-2">
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-sky-300 font-mono text-[11px] border border-slate-700">
              F
            </kbd>
            <span>Toggle fullscreen mode anywhere in the app (when not typing code or text)</span>
          </li>
          <li className="flex items-center gap-2">
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-sky-300 font-mono text-[11px] border border-slate-700">
              Ctrl+Shift+F
            </kbd>
            <span>Universal fullscreen toggle shortcut</span>
          </li>
          <li className="flex items-center gap-2">
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-sky-300 font-mono text-[11px] border border-slate-700">
              Esc
            </kbd>
            <span>Exit fullscreen or dismiss distraction-free Zen mode</span>
          </li>
        </ul>
      </div>
    </Section>
  )
}

