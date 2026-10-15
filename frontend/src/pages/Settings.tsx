import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { EventReadiness, QueueConfig, User } from '../api/types'
import { isAllowedQwenCoderModel, ALLOWED_QWEN_CODER_MODELS } from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import { FullscreenButton, useFullscreen } from '../components/FullscreenContext'



import { useTheme, THEME_REGISTRY, FONT_SIZES, type CognitiveTheme, type FontSize } from '../components/ThemeContext'
import InteractiveTutorialModal from '../components/InteractiveTutorialModal'

export default function Settings() {
  const { user, refresh, signOut } = useAuth()
  const [queueCfg, setQueueCfg] = useState<QueueConfig | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [showTutorial, setShowTutorial] = useState(false)
  const [tutorialMode, setTutorialMode] = useState<'prompt' | 'tour'>('tour')
  const [tutorialType, setTutorialType] = useState<'extensive' | 'brief'>('extensive')

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
      <CognitiveThemePanel />
      <TypographyPanel />
      <DisplayFocusPanel />
      <TutorialPanel
        user={user}
        onLaunchTutorial={(mode, type) => {
          setTutorialMode(mode)
          setTutorialType(type)
          setShowTutorial(true)
        }}
        onChange={refresh}
      />
      <NavigationModulesPanel user={user} onChange={refresh} />
      <SchedulingPanel user={user} onChange={refresh} />
      <QueuePanel cfg={queueCfg} onChange={load} />
      <DataPanel />

      <Section title="Account" description={user.email}>
        <button className="btn btn-danger" onClick={signOut}>
          Sign out
        </button>
      </Section>

      <InteractiveTutorialModal
        isOpen={showTutorial}
        onClose={() => setShowTutorial(false)}
        initialMode={tutorialMode}
        initialType={tutorialType}
      />
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
      title="💻 Local AI Engine (Qwen 2.5 Coder)"
      description="Strictly utilizes quantized Qwen 2.5 Coder models (7B, 3B, 1.5B). Zero cloud costs, zero rate limits, and 100% private."
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
                  <span>{user.grading_model || 'qwen2.5-coder:7b'}</span>
                  <span className="chip text-[10px] px-1.5 py-0.2 border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
                    Active Grader
                  </span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Endpoint: <code className="font-mono text-slate-300">{status?.base_url || 'http://localhost:11434'}</code>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {status?.models_installed &&
                status.models_installed.filter(isAllowedQwenCoderModel).length > 0 && (
                  <select
                    value={user.grading_model}
                    onChange={async (e) => {
                      await api.updateMe({ grading_model: e.target.value })
                      await onChange()
                      void checkStatus()
                    }}
                    className="select text-xs py-1 px-2.5 bg-slate-900 border-slate-700 text-slate-200 font-mono rounded cursor-pointer"
                    title="Switch active local grading model"
                  >
                    {status.models_installed
                      .filter(isAllowedQwenCoderModel)
                      .map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                  </select>
                )}

              <button
                className="btn text-xs py-1.5 px-3"
                disabled={checking}
                onClick={() => void checkStatus()}
              >
                {checking ? 'Testing…' : '↻ Test Connection'}
              </button>
            </div>
          </div>

          {/* Status Diagnostic Callout */}
          {status && (
            <div className="mt-4 pt-3 border-t border-ink-line text-xs">
              {status.connected && status.model_ready ? (
                <div className="flex items-center gap-2 text-emerald-300">
                  <span>✓</span>
                  <span>Ollama is online and <strong>{user.grading_model || 'model'}</strong> is ready to grade solutions.</span>
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

          {/* Supported Quantized Qwen 2.5 Coder Specs */}
          <div className="mt-4 pt-3 border-t border-ink-line space-y-2">
            <span className="text-xs font-semibold text-slate-300">
              Supported Quantized Models (Qwen 2.5 Coder):
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
              {ALLOWED_QWEN_CODER_MODELS.map((opt) => {
                const isInstalled = status?.models_installed?.some(
                  (im) => im.toLowerCase() === opt.id.toLowerCase() || im.toLowerCase().startsWith(opt.id.toLowerCase())
                )
                const isActive = (user.grading_model || 'qwen2.5-coder:7b') === opt.id
                return (
                  <div
                    key={opt.id}
                    className={`rounded-lg border p-2.5 space-y-1.5 transition text-xs ${
                      isActive
                        ? 'border-sky-500/60 bg-sky-950/40'
                        : isInstalled
                        ? 'border-slate-800 bg-slate-900/50'
                        : 'border-slate-800/60 bg-slate-900/20 text-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{opt.name}</span>
                      <span className="text-[10px] font-mono text-slate-400">{opt.vramApprox}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-tight">{opt.desc}</p>
                    <div className="pt-1 flex items-center justify-between text-[11px]">
                      {isInstalled ? (
                        <span className="text-emerald-400 flex items-center gap-1 font-medium">
                          ✓ Installed
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => void navigator.clipboard.writeText(`ollama pull ${opt.id}`)}
                          className="text-[10px] text-sky-400 hover:text-sky-200 underline font-mono cursor-pointer"
                          title={`Click to copy: ollama pull ${opt.id}`}
                        >
                          Copy pull command
                        </button>
                      )}
                      {isActive && (
                        <span className="text-[10px] text-sky-300 font-bold">Active</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
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
        <Field label="Time zone" hint="Daily limits and streaks reset at 4 am here. IANA name, e.g. America/Vancouver.">
          <input
            type="text"
            className="input"
            defaultValue={user.timezone ?? ''}
            onBlur={(e) => {
              const zone = e.target.value.trim()
              if (zone && zone !== user.timezone) void save({ timezone: zone })
            }}
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

function DataPanel() {
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
        reading sources.
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

function TypographyPanel() {
  const { fontSize, setFontSize } = useTheme()

  const sizeLabels: Record<FontSize, { label: string; tag: string }> = {
    10: { label: '10px', tag: 'Tiny / Dense' },
    12: { label: '12px', tag: 'Compact' },
    14: { label: '14px', tag: 'Medium' },
    16: { label: '16px', tag: 'Default' },
    18: { label: '18px', tag: 'Large' },
    20: { label: '20px', tag: 'Extra Large' },
  }

  return (
    <Section
      title="🔤 Typography & Font Size"
      description="Select the application base font size (10px to 20px). The interface, buttons, inputs, and knowledge cards scale smoothly in clean Verdana font."
    >
      <div className="space-y-4">
        {/* Font size pill selector */}
        <div className="flex flex-wrap items-center gap-2.5">
          {FONT_SIZES.map((size) => {
            const isSelected = fontSize === size
            const meta = sizeLabels[size]
            return (
              <button
                key={size}
                type="button"
                onClick={() => setFontSize(size)}
                className={`flex flex-col items-center justify-center rounded-xl border px-3.5 py-2.5 transition cursor-pointer min-w-[5.25rem] ${
                  isSelected
                    ? 'border-sky-500 bg-sky-950/50 text-sky-200 ring-2 ring-sky-500/50 shadow-md'
                    : 'border-ink-line bg-ink/70 text-slate-300 hover:border-slate-600 hover:bg-ink'
                }`}
              >
                <span className="font-bold font-mono text-sm">
                  {meta.label}
                </span>
                <span className={`text-[10px] mt-0.5 ${isSelected ? 'text-sky-300 font-semibold' : 'text-slate-500'}`}>
                  {meta.tag}
                </span>
              </button>
            )
          })}

          {fontSize !== 16 && (
            <button
              type="button"
              onClick={() => setFontSize(16)}
              className="btn text-xs py-2 px-3 text-slate-400 hover:text-slate-200"
              title="Reset font size to 16px default"
            >
              ↺ Reset (16px)
            </button>
          )}
        </div>

        {/* Live Typography Preview Box */}
        <div className="rounded-xl border border-ink-line bg-ink-soft/50 p-4 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 border-b border-ink-line/50 pb-2">
            <span className="font-semibold uppercase tracking-wider text-[11px] text-slate-300">
              Live Verdana Preview ({fontSize}px base scale)
            </span>
            <span className="font-mono text-sky-400 text-[11px]">font-family: 'Verdana', sans-serif</span>
          </div>

          <div className="space-y-1.5 pt-1">
            <h4 className="font-bold text-slate-100" style={{ fontSize: `${fontSize * 1.15}px` }}>
              Active Recall & FSRS Scheduling
            </h4>
            <p className="text-slate-300 leading-relaxed" style={{ fontSize: `${fontSize}px` }}>
              Every function has a contract. Type your answer to verify understanding with local AI reasoning and token-by-token answer similarity checking.
            </p>
            <div className="pt-1">
              <code className="font-mono bg-ink px-2 py-0.5 rounded border border-ink-line text-emerald-300 text-xs inline-block">
                def memory_consolidation(stability: float, difficulty: float) -&gt; float:
              </code>
            </div>
          </div>
        </div>
      </div>
    </Section>
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

function TutorialPanel({
  user,
  onLaunchTutorial,
  onChange,
}: {
  user: User
  onLaunchTutorial: (mode: 'prompt' | 'tour', type: 'extensive' | 'brief') => void
  onChange: () => Promise<void>
}) {
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const toggleCompletion = async () => {
    setResetting(true)
    setError(null)
    try {
      const nextStatus = !user.tutorial_completed
      await api.updateMe({ tutorial_completed: nextStatus })
      if (!nextStatus) {
        localStorage.removeItem('tutorial_prompt_dismissed')
        localStorage.removeItem('prompt_new_user_tutorial')
      }
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setResetting(false)
    }
  }

  return (
    <Section
      title="🎓 Interactive Tutorial & Onboarding Guide"
      description="Walk through or replay the guided onboarding tour anytime. Learn the core principles: Active Recall, local AI grading with the token-by-token answer similarity checker, Knowledge Trees, and the Priority Queue."
    >
      <div className="space-y-4">
        {/* Status Header Bar */}
        <div className="rounded-xl border border-ink-line bg-ink/70 p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🏛️</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-100">Tutorial Onboarding Status</span>
                {user.tutorial_completed ? (
                  <span className="chip border-emerald-500/40 text-emerald-300 bg-emerald-500/10 font-semibold text-[10px]">
                    ✓ Completed
                  </span>
                ) : (
                  <span className="chip border-amber-500/40 text-amber-300 bg-amber-500/10 font-semibold text-[10px]">
                    ⏳ Incomplete / Not Finished
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {user.tutorial_completed
                  ? 'You have completed the introductory tour. You can replay either mode below at any time.'
                  : 'You have not yet marked the introductory tutorial as finished.'}
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={resetting}
            onClick={() => void toggleCompletion()}
            className="btn text-xs py-1.5 px-3 text-slate-300 hover:text-slate-100"
            title="Toggle tutorial completion status"
          >
            {resetting ? 'Updating…' : user.tutorial_completed ? '↺ Reset to Incomplete' : '✓ Mark as Completed'}
          </button>
        </div>

        {/* Tutorial Mode Selection Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {/* Card A: Brief High-Level Tour */}
          <div className="rounded-xl border border-ink-line bg-ink-soft/50 p-4 flex flex-col justify-between space-y-3 hover:border-sky-500/60 transition">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sky-300 font-bold text-xs">
                  <span className="text-base">⚡</span>
                  <span>Brief High-Level Overview</span>
                </div>
                <span className="chip text-[10px] py-0.5 border-sky-500/40 text-sky-300 bg-sky-500/10 font-semibold">
                  1 min
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                A rapid 3-slide executive overview of the core principles: Active Recall, Hierarchical Knowledge Trees with distribution bars, and the Priority Queue.
              </p>
              <ul className="text-[10px] text-slate-500 space-y-1 pt-1">
                <li className="flex items-center gap-1.5">
                  <span className="text-sky-400">✓</span>
                  <span>Slide 1: Active Recall & Token Similarity Grading</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="text-sky-400">✓</span>
                  <span>Slide 2: Knowledge Trees & Visual Progress Bars</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="text-sky-400">✓</span>
                  <span>Slide 3: Priority Queue, Time Bank & Deep Mastery</span>
                </li>
              </ul>
            </div>

            <button
              type="button"
              onClick={() => onLaunchTutorial('tour', 'brief')}
              className="btn btn-primary w-full py-2 text-xs font-semibold"
            >
              Start Brief Overview (1 min) →
            </button>
          </div>

          {/* Card B: Extensive Deep-Dive Interactive Tutorial */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/10 p-4 flex flex-col justify-between space-y-3 hover:border-emerald-500/60 transition">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-300 font-bold text-xs">
                  <span className="text-base">📘</span>
                  <span>Extensive Interactive Tutorial</span>
                </div>
                <span className="chip text-[10px] py-0.5 border-emerald-500/40 text-emerald-300 bg-emerald-500/10 font-semibold">
                  Recommended · 4 min
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Full hands-on interactive simulation: test-drive the FSRS retention slider, simulate live AI grading with the token-by-token similarity checker, and explore branch ordering.
              </p>
              <ul className="text-[10px] text-slate-500 space-y-1 pt-1">
                <li className="flex items-center gap-1.5">
                  <span className="text-emerald-400">✓</span>
                  <span>Steps 0–1: FSRS Retention Simulator & Live AI Grader</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="text-emerald-400">✓</span>
                  <span>Steps 2–3: Interactive Knowledge Tree & Time Bank</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="text-emerald-400">✓</span>
                  <span>Steps 4–5: Incremental Reading, Code Lab & Launchpad</span>
                </li>
              </ul>
            </div>

            <button
              type="button"
              onClick={() => onLaunchTutorial('tour', 'extensive')}
              className="btn btn-primary w-full py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500/50 text-white"
            >
              Start Extensive Tutorial (4 min) →
            </button>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
          <button
            type="button"
            onClick={() => onLaunchTutorial('prompt', 'extensive')}
            className="text-slate-400 hover:text-sky-300 text-xs transition cursor-pointer flex items-center gap-1.5"
          >
            <span>🏛️</span>
            <span>Open Initial Welcome Chooser Modal</span>
          </button>

          <a
            href="/tutorial"
            className="text-slate-400 hover:text-sky-300 text-xs transition flex items-center gap-1"
          >
            <span>View Verified Milestone Checklist (/tutorial)</span>
            <span>→</span>
          </a>
        </div>

        <ErrorNote error={error} />
      </div>
    </Section>
  )
}

function NavigationModulesPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [savingPreLeetCode, setSavingPreLeetCode] = useState(false)
  const [savingCodeLab, setSavingCodeLab] = useState(false)
  const [savingThematicContext, setSavingThematicContext] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const togglePreLeetCode = async () => {
    setSavingPreLeetCode(true)
    setError(null)
    try {
      await api.updateMe({ show_pre_leetcode: !user.show_pre_leetcode })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingPreLeetCode(false)
    }
  }

  const toggleCodeLab = async () => {
    setSavingCodeLab(true)
    setError(null)
    try {
      await api.updateMe({ show_code_lab: !user.show_code_lab })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingCodeLab(false)
    }
  }

  const toggleThematicContext = async () => {
    setSavingThematicContext(true)
    setError(null)
    try {
      await api.updateMe({ show_thematic_context: user.show_thematic_context === false ? true : false })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingThematicContext(false)
    }
  }

  return (
    <Section
      title="Navigation & Modules"
      description="Toggle visibility for specialized study modules in the top navigation bar and study documentation overlays. Disabled modules remain accessible via direct URL."
    >
      <ErrorNote error={error} />
      <div className="space-y-3">
        {/* Pre-LeetCode */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">Pre-LeetCode</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                  user.show_pre_leetcode
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.show_pre_leetcode ? 'Visible' : 'Hidden'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Interactive Python fundamentals, cognitive Socratic tutoring, and code execution sandbox.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(user.show_pre_leetcode)}
            aria-label="Toggle Pre-LeetCode visibility"
            disabled={savingPreLeetCode}
            onClick={togglePreLeetCode}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.show_pre_leetcode ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.show_pre_leetcode ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Code Lab */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">Code Lab</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                  user.show_code_lab
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.show_code_lab ? 'Visible' : 'Hidden'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Targeted coding practice problems, automated test suites, and memory-anchored algorithm drills.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(user.show_code_lab)}
            aria-label="Toggle Code Lab visibility"
            disabled={savingCodeLab}
            onClick={toggleCodeLab}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.show_code_lab ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.show_code_lab ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Thematic Context & Documentation */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">Thematic Context &amp; Documentation</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                  user.show_thematic_context !== false
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.show_thematic_context !== false ? 'Visible' : 'Hidden'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Display attached deck &amp; card documentation, creation source documents, and thematic nature during reviews and card exploration.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={user.show_thematic_context !== false}
            aria-label="Toggle Thematic Context and Documentation visibility"
            disabled={savingThematicContext}
            onClick={toggleThematicContext}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.show_thematic_context !== false ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.show_thematic_context !== false ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>
    </Section>
  )
}

function CognitiveThemePanel() {
  const {
    themeMode,
    setThemeMode,
    fixedTheme,
    setFixedTheme,
    activeThemeMeta,
    setCognitiveContext,
    enableNightAutoShift,
    setEnableNightAutoShift,
    enableOledBlack,
    setEnableOledBlack,
  } = useTheme()

  return (
    <Section
      title="🎨 Cognitive State & Ergonomic Theming"
      description="Choose how the interface adapts to your mental state: automatically transition color harmonies based on active learning, recall, and debugging phases, or lock into a fixed palette."
    >
      <div className="space-y-6">
        {/* Mode Selector Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Option A: Dynamic Context-Adaptive */}
          <div
            onClick={() => setThemeMode('dynamic')}
            className={`rounded-2xl border p-4 cursor-pointer transition-all relative ${
              themeMode === 'dynamic'
                ? 'border-sky-500 bg-sky-950/20 shadow-lg ring-1 ring-sky-500/50'
                : 'border-ink-line bg-ink/60 hover:border-slate-600 hover:bg-ink'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xl">🔀</span>
                <span className="font-bold text-slate-100 text-sm">Dynamic Context-Adaptive</span>
              </div>
              <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                Recommended
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">
              The interface smoothly shifts its color harmony to match your real-time cognitive task:
              calming Azure/Emerald for new learning, high-alert Indigo/Amber for recall questions,
              diagnostic Cyan/Coral when tests fail, and obsidian for code flow.
            </p>
            {themeMode === 'dynamic' && (
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/40 p-2.5 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Current Active State:</span>
                  <span className="font-semibold text-sky-200 flex items-center gap-1.5">
                    <span>{activeThemeMeta.icon}</span>
                    <span>{activeThemeMeta.label}</span>
                  </span>
                </div>
                <div className="pt-2 border-t border-sky-500/20">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableNightAutoShift}
                      onChange={(e) => setEnableNightAutoShift(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500 cursor-pointer"
                    />
                    <span className="text-[11px]">
                      🌙 Automatically shift to <strong>Circadian Candlelight</strong> after 8:00 PM
                    </span>
                  </label>
                </div>
                <div className="pt-2 border-t border-sky-500/20">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableOledBlack}
                      onChange={(e) => setEnableOledBlack(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500 cursor-pointer"
                    />
                    <span className="text-[11px]">
                      🌑 <strong>OLED Pure Black Canvas</strong>: Keep adaptive accents but force pure pitch black (<code>#000000</code>) background
                    </span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Option B: Fixed Palette Lock */}
          <div
            onClick={() => setThemeMode('fixed')}
            className={`rounded-2xl border p-4 cursor-pointer transition-all relative ${
              themeMode === 'fixed'
                ? 'border-sky-500 bg-sky-950/20 shadow-lg ring-1 ring-sky-500/50'
                : 'border-ink-line bg-ink/60 hover:border-slate-600 hover:bg-ink'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xl">🔒</span>
                <span className="font-bold text-slate-100 text-sm">Fixed Palette Lock</span>
              </div>
              <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
                User Choice
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">
              Lock in one uniform color scheme across the entire application. Your chosen substrate and
              accent pairing stays consistent across Flashcards, Code Lab, Reading, and Tree views.
            </p>
            {themeMode === 'fixed' && (
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/40 p-2.5 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Locked Palette:</span>
                  <span className="font-semibold text-sky-200 flex items-center gap-1.5">
                    <span>{activeThemeMeta.icon}</span>
                    <span>{activeThemeMeta.label}</span>
                  </span>
                </div>
                <div className="pt-2 border-t border-sky-500/20">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableOledBlack}
                      onChange={(e) => setEnableOledBlack(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500 cursor-pointer"
                    />
                    <span className="text-[11px]">
                      🌑 <strong>OLED Pure Black Canvas</strong>: Force pure pitch black (<code>#000000</code>) background
                    </span>
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Palettes Grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              {themeMode === 'fixed' ? 'Choose Your Fixed Palette:' : 'Interactive Cognitive State Previews:'}
            </h4>
            {themeMode === 'dynamic' && (
              <span className="text-[11px] text-slate-500 italic">
                (Click any state to preview its color scheme)
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {(Object.keys(THEME_REGISTRY) as CognitiveTheme[]).map((themeKey) => {
              const meta = THEME_REGISTRY[themeKey]
              const isSelected =
                themeMode === 'fixed' ? fixedTheme === themeKey : activeThemeMeta.id === themeKey

              return (
                <div
                  key={themeKey}
                  onClick={() => {
                    if (themeMode === 'dynamic') {
                      setCognitiveContext(themeKey === 'classic' ? null : themeKey)
                    } else {
                      setFixedTheme(themeKey)
                    }
                  }}
                  className={`rounded-xl border p-3.5 transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'border-sky-500/70 bg-sky-950/30 shadow-md ring-1 ring-sky-500/40'
                      : 'border-ink-line/80 bg-ink-soft/40 hover:border-slate-600 hover:bg-ink-soft'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{meta.icon}</span>
                        <span className="font-semibold text-slate-200 text-xs">{meta.label}</span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className="w-3.5 h-3.5 rounded-full border border-white/30 shadow-sm"
                          style={{ backgroundColor: meta.primaryColor }}
                          title={`Primary Accent: ${meta.primaryColor}`}
                        />
                        <span
                          className="w-3.5 h-3.5 rounded-full border border-white/30 shadow-sm"
                          style={{ backgroundColor: meta.secondaryColor }}
                          title={`Secondary Accent: ${meta.secondaryColor}`}
                        />
                      </div>
                    </div>
                    <p className="text-[11px] font-mono text-slate-400 mb-2">{meta.subtitle}</p>
                    <p className="text-[11px] text-slate-300 leading-snug mb-2 font-medium">
                      🎯 <span className="text-slate-400">{meta.bestFor}</span>
                    </p>
                    <p className="text-[10px] text-slate-500 leading-normal italic">
                      🧠 {meta.psychology}
                    </p>
                  </div>

                  <div className="mt-3 pt-2 border-t border-ink-line/50 flex items-center justify-between text-[11px]">
                    <span className="text-slate-500 font-mono text-[10px]">
                      {meta.primaryColor} / {meta.secondaryColor}
                    </span>
                    <button
                      type="button"
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold transition cursor-pointer ${
                        isSelected
                          ? 'bg-sky-500/30 text-sky-200 border border-sky-500/50'
                          : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {isSelected ? '✓ Active' : themeMode === 'fixed' ? 'Select' : 'Preview'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </Section>
  )
}


