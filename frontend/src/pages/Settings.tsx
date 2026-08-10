import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { QueueConfig, User } from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

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
              setModels(resp.models)
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
            setModels(resp.available_models)
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
          <p className="label">Models this key can reach</p>
          <div className="flex flex-wrap gap-1.5">
            {models.map((m) => (
              <button
                key={m}
                className={`chip transition hover:border-sky-500/50 ${
                  user.grading_model === m ? 'border-sky-500/50 text-sky-200' : ''
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
            Click one to use it for grading. Currently: {user.grading_model}
          </p>
        </div>
      )}
    </Section>
  )
}

function GradingPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  return (
    <Section
      title="LLM grading"
      description="You type an answer; the model grades it and shows its reasoning; you accept or override."
    >
      <div className="space-y-4">
        {/* §15: consent must be explicit — answers and reading text leave the box. */}
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
            <span className="text-slate-200">Send my answers to Google for grading</span>
            <span className="mt-1 block text-xs text-slate-500">
              Your typed answers, the card's text, and any reading passages you run "LLM assist" on
              are sent to Google's API under your own key. Leave this off and everything works with
              manual grading instead — that fallback is a full path, not a degraded one.
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
            <span className="text-slate-200">Ask the model to fix cards I keep failing</span>
            <span className="mt-1 block text-xs text-slate-500">
              One extra call per leech (not per review). Off means plain auto-suspend.
            </span>
          </span>
        </label>

        <Field
          label="Grading model"
          hint="The escalation model is configured server-side for low-confidence and math/code cards."
        >
          <input
            className="input"
            defaultValue={user.grading_model}
            onBlur={async (e) => {
              if (e.target.value !== user.grading_model) {
                await api.updateMe({ grading_model: e.target.value })
                await onChange()
              }
            }}
          />
        </Field>
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
