import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Leech, SisterPair, Stats as StatsData } from '../api/types'
import { Empty, ErrorNote, Section, Spinner } from '../components/ui'

export default function Stats() {
  const [stats, setStats] = useState<StatsData | null>(null)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    try {
      setStats(await api.stats())
    } catch (err) {
      setError(err)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (error) return <ErrorNote error={error} />
  if (!stats) return <Spinner />

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Cards" value={stats.totals.cards} />
        <Stat label="In review" value={stats.totals.review} />
        <Stat label="Reviews logged" value={stats.totals.reviews_logged} />
        <Stat
          label="Avg stability"
          value={stats.totals.avg_stability_days}
          suffix="d"
          hint="Days until recall falls to 90%"
        />
      </div>

      <Section title="Activity" description="Reviews per day over the last year.">
        <Heatmap data={stats.heatmap} />
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Forecast" description="Cards coming due over the next 30 days.">
          <Bars data={stats.forecast} color="bg-sky-400/70" />
        </Section>

        <Section
          title="Retention"
          description="How often you recalled a card, bucketed by how long it was left."
        >
          {Object.keys(stats.retention).length === 0 ? (
            <Empty title="Not enough review history yet." />
          ) : (
            <div className="space-y-2">
              {Object.entries(stats.retention).map(([bucket, rate]) => (
                <div key={bucket} className="flex items-center gap-3">
                  <span className="w-16 text-xs text-slate-500">{bucket}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-line">
                    <div
                      className="h-full rounded-full bg-emerald-400/70"
                      style={{ width: `${rate * 100}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-xs tabular-nums text-slate-400">
                    {Math.round(rate * 100)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="LLM grading" description="How much you agree with the model (§4.3).">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Row label="Answers graded" value={stats.grading.llm_graded} />
            <Row label="Agreement" value={`${Math.round(stats.grading.agreement_rate * 100)}%`} />
            <Row label="Override rate" value={`${Math.round(stats.grading.override_rate * 100)}%`} />
            <Row
              label="Calibration bias"
              value={stats.grading.bias.toFixed(2)}
              hint={
                stats.grading.bias > 0.1
                  ? 'grades you harshly — corrected upward'
                  : stats.grading.bias < -0.1
                    ? 'grades you leniently — corrected downward'
                    : 'well calibrated'
              }
            />
          </dl>
        </Section>

        <Section title="Reading throughput" description="Incremental reading progress (§8).">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Row label="Active sources" value={stats.ir_throughput.sources_active} />
            <Row label="Extracts left" value={stats.ir_throughput.extracts_active} />
            <Row label="Extracts done" value={stats.ir_throughput.extracts_done} />
            <Row label="Cards from reading" value={stats.ir_throughput.cards_from_reading} />
          </dl>
        </Section>
      </div>

      <Leeches leeches={stats.leeches} onChange={load} />
      <Interference />
    </div>
  )
}

const PAIR_COPY: Record<string, { label: string; hint: string; tone: string }> = {
  interference: {
    label: 'Confusable',
    hint: 'These look alike but have different answers — the pair most likely to be tripping you up.',
    tone: 'text-rose-300',
  },
  duplicate: {
    label: 'Duplicate',
    hint: 'Near-identical on both sides. Consider deleting one.',
    tone: 'text-amber-300',
  },
  convergent: {
    label: 'Same answer',
    hint: 'Two different prompts with the same answer. Usually fine, sometimes redundant.',
    tone: 'text-slate-400',
  },
}

/** Sister-card interference (§2, §14 Phase 4). Detected locally — no API cost. */
function Interference() {
  const [pairs, setPairs] = useState<SisterPair[]>([])
  const [scanning, setScanning] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    try {
      setPairs(await api.sisterPairs())
    } catch (err) {
      setError(err)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function scan() {
    setScanning(true)
    setError(null)
    try {
      const r = await api.scanInterference()
      const kinds = Object.entries(r.by_kind)
        .map(([k, v]) => `${v} ${PAIR_COPY[k]?.label.toLowerCase() ?? k}`)
        .join(', ')
      setSummary(
        `Scanned ${r.notes_scanned} notes — ${r.pairs_found} pair${r.pairs_found === 1 ? '' : 's'}${
          kinds ? ` (${kinds})` : ''
        }.`,
      )
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setScanning(false)
    }
  }

  return (
    <Section
      title={`Confusable cards (${pairs.length})`}
      description="Cards similar enough to interfere with each other. Flagged pairs are also kept apart within a review session."
      actions={
        <button className="btn" onClick={scan} disabled={scanning}>
          {scanning ? 'Scanning…' : 'Scan collection'}
        </button>
      }
    >
      {summary && <p className="mb-3 text-xs text-slate-500">{summary}</p>}
      <ErrorNote error={error} />

      {pairs.length === 0 ? (
        <Empty title="No confusable pairs found.">
          Run a scan after adding cards. It runs locally — no API calls, no cost.
        </Empty>
      ) : (
        <div className="space-y-3">
          {pairs.map((p) => {
            const copy = PAIR_COPY[p.kind] ?? PAIR_COPY.convergent
            return (
              <div key={p.id} className="rounded-lg border border-ink-line p-4">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className={`chip ${copy.tone}`}>{copy.label}</span>
                  <span className="chip">front {Math.round(p.front_similarity * 100)}%</span>
                  <span className="chip">back {Math.round(p.back_similarity * 100)}%</span>
                </div>
                <p className="mt-2 text-xs text-slate-600">{copy.hint}</p>

                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {[
                    { front: p.front_a, back: p.back_a },
                    { front: p.front_b, back: p.back_b },
                  ].map((n, i) => (
                    <div key={i} className="rounded border border-ink-line bg-ink p-3">
                      <p className="text-sm text-slate-200">{n.front}</p>
                      <p className="mt-1 text-sm text-slate-500">{n.back}</p>
                    </div>
                  ))}
                </div>

                <button
                  className="btn mt-3 px-2.5 py-1 text-xs"
                  onClick={async () => {
                    await api.dismissPair(p.id)
                    await load()
                  }}
                >
                  These don't confuse me
                </button>
              </div>
            )
          })}
        </div>
      )}
    </Section>
  )
}

function Stat({
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
    <div className="card" title={hint}>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
        {Math.round(value).toLocaleString()}
        {suffix && <span className="ml-0.5 text-base text-slate-500">{suffix}</span>}
      </p>
    </div>
  )
}

function Row({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="tabular-nums text-slate-200">{value}</dd>
      {hint && <dd className="text-xs text-slate-600">{hint}</dd>}
    </div>
  )
}

function Heatmap({ data }: { data: Record<string, number> }) {
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
    if (n === 0) return 'bg-ink-line'
    const r = n / max
    if (r > 0.66) return 'bg-emerald-400'
    if (r > 0.33) return 'bg-emerald-500/70'
    return 'bg-emerald-600/50'
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
                title={`${d.date}: ${d.count} review${d.count === 1 ? '' : 's'}`}
                className={`h-2.5 w-2.5 rounded-[2px] ${level(d.count)}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function Bars({ data, color }: { data: Record<string, number>; color: string }) {
  const entries = Object.entries(data).sort(([a], [b]) => a.localeCompare(b)).slice(0, 30)
  if (entries.length === 0) return <Empty title="Nothing scheduled in the next 30 days." />
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

function Leeches({ leeches, onChange }: { leeches: Leech[]; onChange: () => void }) {
  const [busy, setBusy] = useState<string | null>(null)

  async function run(cardId: string, fn: () => Promise<unknown>) {
    setBusy(cardId)
    try {
      await fn()
      onChange()
    } finally {
      setBusy(null)
    }
  }

  return (
    <Section
      title={`Leeches (${leeches.length})`}
      description="Cards you keep failing. The model proposes a fix rather than just suspending them (§3.2)."
    >
      {leeches.length === 0 ? (
        <Empty title="No leeches — nothing is stuck." />
      ) : (
        <div className="space-y-3">
          {leeches.map((l) => (
            <div key={l.card_id} className="rounded-lg border border-ink-line p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="chip text-rose-300">{l.lapse_count} lapses</span>
                {l.deck_name && <span className="chip">{l.deck_name}</span>}
                {l.suggestion_kind && <span className="chip">suggests: {l.suggestion_kind}</span>}
              </div>
              <p className="mt-2 text-sm text-slate-200">{l.front}</p>
              <p className="text-sm text-slate-500">{l.back}</p>

              {l.suggestion_rationale && (
                <div className="mt-3 rounded border border-sky-500/25 bg-sky-500/5 p-3">
                  <p className="text-xs text-sky-200/90">{l.suggestion_rationale}</p>
                  {l.suggested_cards.length > 0 && (
                    <ul className="mt-2 space-y-1 text-xs text-slate-400">
                      {l.suggested_cards.map((c, i) => (
                        <li key={i}>
                          <span className="text-slate-300">{c.front}</span> → {c.back}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              <div className="mt-3 flex flex-wrap gap-2">
                {l.suggestion_kind && l.suggestion_kind !== 'ambiguous' && (
                  <button
                    className="btn btn-primary px-2.5 py-1 text-xs"
                    disabled={busy === l.card_id}
                    onClick={() => run(l.card_id, () => api.acceptLeech(l.card_id))}
                  >
                    Apply {l.suggestion_kind}
                  </button>
                )}
                <button
                  className="btn px-2.5 py-1 text-xs"
                  disabled={busy === l.card_id}
                  onClick={() => run(l.card_id, () => api.dismissLeech(l.card_id))}
                >
                  Keep as is
                </button>
                <button
                  className="btn px-2.5 py-1 text-xs"
                  disabled={busy === l.card_id}
                  onClick={() => run(l.card_id, () => api.suspendLeech(l.card_id))}
                >
                  Suspend
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
