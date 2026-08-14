import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { QueueConfig, User } from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

interface ModelOption {
  id: string
  name: string
  family: 'flash' | 'pro' | 'gemma'
  familyLabel: string
  badge: string
  badgeTone: string
  description: string
  highlight?: boolean
}

// Curated active models: modern Gemini 2.x/3.x and Gemma 2 line.
// Older superseded models (e.g. Gemini 1.0, Gemini 1.5, Gemma 1.x) are excluded.
const RECENT_MODELS: ModelOption[] = [
  // ── Gemini Flash Line ───────────────────────────────────────────────────────
  {
    id: 'gemini-2.5-flash',
    name: 'Gemini 2.5 Flash',
    family: 'flash',
    familyLabel: 'Flash',
    badge: 'Recommended',
    badgeTone: 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10',
    description: "Google's newest multimodal flash model. Ultra-fast, strong evaluation reasoning, and generous rate limits.",
    highlight: true,
  },
  {
    id: 'gemini-2.0-flash',
    name: 'Gemini 2.0 Flash',
    family: 'flash',
    familyLabel: 'Flash',
    badge: 'High Speed',
    badgeTone: 'border-sky-500/40 text-sky-300 bg-sky-500/10',
    description: 'Fast, cost-effective model optimized for low-latency review grading and card generation.',
  },
  {
    id: 'gemini-2.0-flash-lite',
    name: 'Gemini 2.0 Flash Lite',
    family: 'flash',
    familyLabel: 'Flash',
    badge: 'High Quota',
    badgeTone: 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10',
    description: 'Ultra-lightweight throughput model with maximum RPM headroom on free-tier keys.',
  },
  {
    id: 'gemini-3.7-flash',
    name: 'Gemini 3.7 Flash',
    family: 'flash',
    familyLabel: 'Flash',
    badge: 'Hybrid Preview',
    badgeTone: 'border-indigo-500/40 text-indigo-300 bg-indigo-500/10',
    description: 'Next-gen hybrid architecture with dynamic reasoning capabilities.',
  },

  // ── Gemini Pro Line ─────────────────────────────────────────────────────────
  {
    id: 'gemini-2.5-pro',
    name: 'Gemini 2.5 Pro',
    family: 'pro',
    familyLabel: 'Pro',
    badge: 'Frontier Reasoning',
    badgeTone: 'border-purple-500/40 text-purple-300 bg-purple-500/10',
    description: "Google's flagship reasoning model for intricate conceptual evaluation and STEM deductions.",
  },
  {
    id: 'gemini-2.0-pro-exp-02-05',
    name: 'Gemini 2.0 Pro Exp',
    family: 'pro',
    familyLabel: 'Pro',
    badge: 'Experimental Pro',
    badgeTone: 'border-violet-500/40 text-violet-300 bg-violet-500/10',
    description: 'Specialized deep reasoning model with enhanced mathematical and coding deduction.',
  },

  // ── Gemma Line (Open Weights) ──────────────────────────────────────────────
  {
    id: 'gemma-2-9b-it',
    name: 'Gemma 2 (9B)',
    family: 'gemma',
    familyLabel: 'Gemma',
    badge: 'Open Weights',
    badgeTone: 'border-amber-500/40 text-amber-300 bg-amber-500/10',
    description: 'High-accuracy 9B open instruction model. Excellent structured grading without vendor lock-in.',
    highlight: true,
  },
  {
    id: 'gemma-2-27b-it',
    name: 'Gemma 2 (27B)',
    family: 'gemma',
    familyLabel: 'Gemma',
    badge: 'Largest Gemma',
    badgeTone: 'border-amber-500/40 text-amber-300 bg-amber-500/10',
    description: 'Flagship 27B dense Gemma model. Highly competitive with large proprietary models on recall tasks.',
  },
  {
    id: 'gemma-2-2b-it',
    name: 'Gemma 2 (2B)',
    family: 'gemma',
    familyLabel: 'Gemma',
    badge: 'Compact Open',
    badgeTone: 'border-amber-500/40 text-amber-300 bg-amber-500/10',
    description: 'Ultra-compact 2B open model designed for rapid inference with minimal footprint.',
  },
]

function isRecentModel(m: string): boolean {
  const s = m.toLowerCase()
  // Filter out older 1.0, 1.5, legacy previews and non-text models
  if (
    s.startsWith('gemini-1.0') ||
    s.startsWith('gemini-1.5') ||
    s.includes('-001') ||
    s.includes('-002') ||
    s.includes('embedding') ||
    s.includes('aqa') ||
    s.includes('imagen') ||
    s.includes('native-audio') ||
    s.startsWith('gemma-1.') ||
    s.startsWith('gemma-7b')
  ) {
    return false
  }
  return true
}

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
      <ApiKeyPanel user={user} onChange={refresh} />
      <GradingPanel user={user} onChange={refresh} />
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

function ApiKeyPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [key, setKey] = useState('')
  const [busy, setBusy] = useState(false)
  const [models, setModels] = useState<string[]>([])
  const [warning, setWarning] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)

  return (
    <Section
      title="Google API key (BYOK)"
      description="Grading runs on your own key against Google's API — nothing is hosted here, and nothing is shared."
    >
      {user.has_api_key ? (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span className="chip">stored: {user.api_key_masked}</span>
          <button
            className="btn btn-danger px-2.5 py-1 text-xs"
            onClick={async () => {
              await api.deleteKey()
              await onChange()
            }}
          >
            Remove key
          </button>
          <button
            className="btn px-2.5 py-1 text-xs"
            onClick={async () => {
              const resp = await api.models()
              setModels(resp.models.filter(isRecentModel))
              if (resp.error) setWarning(resp.error)
            }}
          >
            List available models
          </button>
        </div>
      ) : (
        <p className="mb-4 text-xs text-slate-500">
          Get one free at aistudio.google.com. Without a key the app still works — grading falls
          back to the four manual buttons.
        </p>
      )}

      <form
        className="flex flex-wrap gap-2"
        onSubmit={async (e) => {
          e.preventDefault()
          setBusy(true)
          setError(null)
          setWarning(null)
          try {
            const resp = await api.storeKey(key)
            setKey('')
            setModels(resp.available_models.filter(isRecentModel))
            setWarning(resp.warning)
            await onChange()
          } catch (err) {
            setError(err)
          } finally {
            setBusy(false)
          }
        }}
      >
        <input
          className="input flex-1"
          type="password"
          placeholder={user.has_api_key ? 'Rotate key…' : 'Paste your Google API key'}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          required
          minLength={10}
        />
        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Verifying…' : user.has_api_key ? 'Rotate' : 'Save key'}
        </button>
      </form>

      <ErrorNote error={error} />

      {warning && (
        <p className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {warning}
        </p>
      )}

      {models.length > 0 && (
        <div className="mt-4">
          <p className="label">Recent models this key can reach ({models.length})</p>
          <div className="flex flex-wrap gap-1.5">
            {models.map((m) => (
              <button
                key={m}
                className={`chip transition hover:border-sky-500/50 ${
                  user.grading_model === m ? 'border-sky-500/50 text-sky-200 bg-sky-500/10' : ''
                }`}
                onClick={async () => {
                  await api.updateMe({ grading_model: m })
                  await onChange()
                }}
              >
                {m}
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-600">
            Click one to activate. Currently active: {user.grading_model}
          </p>
        </div>
      )}
    </Section>
  )
}

function GradingPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [filter, setFilter] = useState<'all' | 'flash' | 'pro' | 'gemma'>('all')
  const [customOpen, setCustomOpen] = useState(false)
  const [customModel, setCustomModel] = useState(user.grading_model)
  const [switching, setSwitching] = useState<string | null>(null)

  const activeOption = RECENT_MODELS.find((m) => m.id === user.grading_model)
  const filteredModels = RECENT_MODELS.filter((m) => filter === 'all' || m.family === filter)

  async function selectModel(id: string) {
    setSwitching(id)
    try {
      await api.updateMe({ grading_model: id })
      await onChange()
    } finally {
      setSwitching(null)
    }
  }

  return (
    <Section
      title="LLM grading & model selection"
      description="Select the evaluation model for active recall scoring, Socratic guidance, and card generation."
    >
      <div className="space-y-6">
        {/* Consent toggles */}
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
              <span className="font-medium text-slate-200">Send my answers to Google for grading</span>
              <span className="mt-0.5 block text-xs text-slate-400">
                Your typed answers, card prompts, and reading extracts are sent to Google's API under your own BYOK key.
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
              <span className="font-medium text-slate-200">Ask the model to fix cards I keep failing</span>
              <span className="mt-0.5 block text-xs text-slate-400">
                One extra remediation diagnosis per leech. Off means plain auto-suspend.
              </span>
            </span>
          </label>
        </div>

        {/* Quick Selection Menu */}
        <div>
          {user.grading_model.startsWith('gemma') && (
            <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3.5 text-xs text-amber-200">
              <p className="font-semibold text-amber-100 flex items-center gap-1.5">
                <span>⚠️</span> Gemma Model Selected on Google AI Studio Key
              </p>
              <p className="mt-1 leading-relaxed text-amber-200/90">
                Google AI Studio keys (<code className="font-mono">aistudio.google.com</code>) serve the hosted <strong>Gemini</strong> models. Gemma is an open-weights model designed for local deployment (Ollama/vLLM) or Vertex AI endpoints, so calling it with an AI Studio key returns <code>404 NOT FOUND</code>.
              </p>
              <button
                type="button"
                className="btn btn-primary mt-2.5 text-xs py-1 px-3"
                onClick={() => selectModel('gemini-2.5-flash')}
              >
                Switch to Gemini 2.5 Flash (Recommended)
              </button>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Select Grading Model</h3>
              <p className="text-xs text-slate-400">
                Curated recent generation models. Older superseded models are excluded.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Current:</span>
              <span className="chip border-sky-500/50 bg-sky-500/10 text-sky-200 font-mono text-xs">
                {user.grading_model}
              </span>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="mt-3 flex flex-wrap gap-1.5 border-b border-ink-line pb-3 text-xs">
            {(
              [
                ['all', 'All Recent Models'],
                ['flash', '⚡ Gemini Flash (Fast)'],
                ['pro', '🧠 Gemini Pro (Reasoning)'],
                ['gemma', '💎 Gemma Line (Open)'],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setFilter(key)}
                className={`rounded-md px-2.5 py-1 font-medium transition ${
                  filter === key
                    ? 'bg-sky-500/20 text-sky-200 ring-1 ring-sky-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-ink'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Model Card Grid */}
          <div className="mt-3 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {filteredModels.map((m) => {
              const isSelected = user.grading_model === m.id
              const isBusy = switching === m.id

              return (
                <div
                  key={m.id}
                  onClick={() => !isSelected && selectModel(m.id)}
                  className={`group relative flex flex-col justify-between rounded-xl border p-3.5 transition-all cursor-pointer ${
                    isSelected
                      ? 'border-sky-500/70 bg-sky-500/10 shadow-sm shadow-sky-500/10 ring-1 ring-sky-500/50'
                      : 'border-ink-line bg-ink/50 hover:border-slate-700 hover:bg-ink'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-1.5">
                      <h4 className="text-xs font-semibold text-slate-100">{m.name}</h4>
                      <span className={`chip text-[10px] px-1.5 py-0.2 ${m.badgeTone}`}>
                        {m.badge}
                      </span>
                    </div>
                    <code className="mt-1 block text-[11px] text-slate-400 font-mono">
                      {m.id}
                    </code>
                    <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                      {m.description}
                    </p>
                    {m.family === 'gemma' && (
                      <span className="mt-2 block rounded bg-amber-500/10 border border-amber-500/30 p-1.5 text-[10px] text-amber-300 leading-tight">
                        Requires Vertex AI or self-hosted endpoint (not hosted on Google AI Studio keys).
                      </span>
                    )}
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-ink-line/60 pt-2 text-xs">
                    <span className="text-[11px] text-slate-500 uppercase tracking-wider">
                      {m.familyLabel}
                    </span>
                    {isSelected ? (
                      <span className="flex items-center gap-1 font-medium text-sky-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulse" />
                        Active
                      </span>
                    ) : (
                      <span className="text-slate-500 group-hover:text-slate-300 transition">
                        {isBusy ? 'Activating…' : 'Select →'}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Custom Model Toggle */}
          <div className="mt-4 border-t border-ink-line pt-3">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setCustomOpen(!customOpen)}
                className="text-xs text-slate-500 hover:text-slate-300 underline"
              >
                {customOpen ? 'Hide custom model input' : 'Enter custom or fine-tuned model ID…'}
              </button>
              {!activeOption && (
                <span className="text-xs text-amber-300/80">
                  Using custom model: <code className="font-mono text-amber-200">{user.grading_model}</code>
                </span>
              )}
            </div>

            {customOpen && (
              <div className="mt-2 flex gap-2">
                <input
                  className="input flex-1 font-mono text-xs"
                  placeholder="e.g. gemini-2.5-flash or custom-model-id"
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                />
                <button
                  type="button"
                  className="btn btn-primary text-xs px-3"
                  onClick={() => customModel.trim() && selectModel(customModel.trim())}
                >
                  Apply Custom Model
                </button>
              </div>
            )}
          </div>
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
