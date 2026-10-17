import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type {
  Bank,
  ChronotypeHour,
  DiscriminatedCard,
  FatiguePoint,
  LearningAnalytics,
  Leech,
  SisterPair,
  Stats as StatsData,
  YieldPoint,
} from '../api/types'
import { formatBanked } from '../components/SessionTimer'
import { Empty, ErrorNote, Section, Spinner } from '../components/ui'

export default function Stats() {
  const [stats, setStats] = useState<StatsData | null>(null)
  const [analytics, setAnalytics] = useState<LearningAnalytics | null>(null)
  const [bank, setBank] = useState<Bank | null>(null)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    try {
      setStats(await api.stats())
    } catch (err) {
      setError(err)
    }
    try {
      setAnalytics(await api.learningAnalytics())
    } catch {
      /* supplementary analytics */
    }
    try {
      setBank(await api.bank())
    } catch {
      /* the bank is supplementary — never block the rest of Stats on it */
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (error) return <ErrorNote error={error} />
  if (!stats) return <Spinner />

  return (
    <div className="space-y-8">
      {/* ── Topline Cards ── */}
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

      {bank && <TimeBank bank={bank} />}

      <Velocity velocity={stats.velocity} />

      {/* ── Learning Science Suite ── */}
      {analytics && (
        <div className="space-y-6 rounded-2xl border border-sky-500/20 bg-sky-950/10 p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-line pb-4">
            <div>
              <h2 className="text-lg font-semibold text-sky-200">Learning Analytics</h2>
              <p className="text-xs text-slate-400">
                Cognitive load, chronobiology, psychometrics, and metacognition.
              </p>
            </div>
            <span className="chip border-sky-500/40 bg-sky-500/10 text-sky-300">
              Active
            </span>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <CognitiveFatigue fatigue={analytics.fatigue} />
            <CircadianChronotype chronotype={analytics.chronotype} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <DesirableDifficultyView difficulty={analytics.desirable_difficulty} />
            <MetacognitiveCalibration metacognition={analytics.metacognition} />
          </div>

          <ItemDiscriminationTriage discrimination={analytics.item_discrimination} />

          <EWMAMasteryAndSPRT
            ewmaScores={analytics.ewma_mastery}
            sprtVerdicts={analytics.sprt_gating}
          />
        </div>
      )}

      {/* ── Core Review Activity & Retention ── */}
      <Section title="Activity" description="Reviews per day (1 year).">
        <Heatmap data={stats.heatmap} />
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Forecast" description="Upcoming cards (30 days).">
          <Bars data={stats.forecast} color="bg-sky-400/70" />
        </Section>

        <Section
          title="Retention"
          description="Recall rate by interval."
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
        <Section title="LLM grading" description="Agreement with model.">
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

        <Section title="Reading throughput" description="Incremental reading progress.">
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

// ── 1. Cognitive Fatigue & Focus Horizon Component ───────────────────────────

function CognitiveFatigue({ fatigue }: { fatigue: LearningAnalytics['fatigue'] }) {
  const curve = fatigue.curve || []
  return (
    <Section
      title="Cognitive Fatigue"
      description="Recall accuracy and latency over session duration."
    >
      <div className="mb-3 rounded-lg border border-sky-500/20 bg-sky-500/5 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-base font-semibold text-sky-200">
              Optimal Focus Block: {fatigue.optimal_focus_minutes}m
            </span>
            <span className="chip border-emerald-500/30 text-emerald-300">
              {Math.round(fatigue.baseline_accuracy * 100)}% Peak Recall
            </span>
          </div>
        </div>
        <p className="mt-1 text-xs text-slate-400">{fatigue.recommendation}</p>
      </div>

      {curve.length === 0 ? (
        <Empty title="Complete timed sessions to measure your focus curve." />
      ) : (
        <div className="space-y-2">
          {curve.map((pt: FatiguePoint) => {
            const accPct = Math.round(pt.accuracy * 100)
            const isSlump = pt.elapsed_minutes > fatigue.optimal_focus_minutes
            return (
              <div key={pt.minute_bucket} className="flex items-center gap-3 text-xs">
                <span className="w-14 text-slate-500 tabular-nums">{pt.minute_bucket}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-line">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isSlump ? 'bg-amber-400/80' : 'bg-sky-400/80'
                    }`}
                    style={{ width: `${accPct}%` }}
                  />
                </div>
                <span className="w-12 text-right tabular-nums text-slate-300">{accPct}%</span>
                <span className="w-16 text-right tabular-nums text-slate-500">
                  {pt.avg_latency_ms ? `${Math.round(pt.avg_latency_ms / 100) / 10}s` : '—'}
                </span>
              </div>
            )
          })}
          <div className="flex justify-between pt-1 text-[11px] text-slate-600">
            <span>Elapsed session minutes</span>
            <span>Accuracy / Latency</span>
          </div>
        </div>
      )}
    </Section>
  )
}

// ── 2. Circadian Chronotype Efficiency ───────────────────────────────────────

function CircadianChronotype({ chronotype }: { chronotype: LearningAnalytics['chronotype'] }) {
  const hourly = chronotype.hourly || []
  const maxEff = Math.max(1, ...hourly.map((h: ChronotypeHour) => h.efficiency_score))

  return (
    <Section
      title="Circadian Chronotype"
      description="Efficiency by hour of day (0–23)."
    >
      <div className="mb-3 rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold text-indigo-200">
            Peak Window: {chronotype.optimal_study_time || '09:00 - 12:00'}
          </span>
          <span className="chip border-indigo-500/30 text-indigo-300">Circadian Peak</span>
        </div>
        <p className="mt-1 text-xs text-slate-400">{chronotype.summary}</p>
      </div>

      <div className="grid grid-cols-12 gap-1 pt-2">
        {hourly.map((h: ChronotypeHour) => {
          const isPeak =
            (h.hour >= chronotype.peak_window_start && h.hour < chronotype.peak_window_end) ||
            (chronotype.peak_window_start > chronotype.peak_window_end &&
              (h.hour >= chronotype.peak_window_start || h.hour < chronotype.peak_window_end))
          const heightPct = h.efficiency_score > 0 ? Math.max(10, (h.efficiency_score / maxEff) * 100) : 4

          return (
            <div
              key={h.hour}
              className="group relative flex flex-col items-center"
              title={`${h.hour}:00 — ${h.review_count} reviews, ${Math.round(h.accuracy * 100)}% accuracy, ${
                h.avg_latency_ms ? `${Math.round(h.avg_latency_ms)}ms` : ''
              }`}
            >
              <div className="h-16 w-full flex items-end justify-center rounded bg-ink-line/40 p-0.5">
                <div
                  className={`w-full rounded-t transition-all ${
                    isPeak
                      ? 'bg-indigo-400 group-hover:bg-indigo-300'
                      : h.review_count > 0
                        ? 'bg-slate-500 group-hover:bg-slate-400'
                        : 'bg-slate-700/30'
                  }`}
                  style={{ height: `${heightPct}%` }}
                />
              </div>
              <span className="mt-1 text-[10px] text-slate-500 tabular-nums">
                {h.hour % 4 === 0 ? `${h.hour}h` : ''}
              </span>
            </div>
          )
        })}
      </div>
      <div className="flex justify-between pt-1 text-[11px] text-slate-600">
        <span>00:00 (Midnight)</span>
        <span>12:00 (Noon)</span>
        <span>23:00 (Night)</span>
      </div>
    </Section>
  )
}

// ── 3. Desirable Difficulty & Yield Curve ─────────────────────────────────────

function DesirableDifficultyView({ difficulty }: { difficulty: LearningAnalytics['desirable_difficulty'] }) {
  const curve = difficulty.curve || []
  return (
    <Section
      title="Desirable Difficulty"
      description="Stability gain (ΔS) relative to retrievability."
    >
      <div className="mb-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold text-emerald-200">
            Target Retention: {Math.round(difficulty.optimal_retention_target * 100)}%
          </span>
          <span className="chip border-emerald-500/30 text-emerald-300">Optimal Yield Zone</span>
        </div>
        <p className="mt-1 text-xs text-slate-400">{difficulty.summary}</p>
      </div>

      {curve.length === 0 ? (
        <Empty title="Review mature cards to generate your retrievability yield curve." />
      ) : (
        <div className="space-y-2">
          {curve.map((pt: YieldPoint) => (
            <div key={pt.retrievability_bucket} className="flex items-center gap-3 text-xs">
              <span className="w-16 text-slate-500">{pt.retrievability_bucket}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-line">
                <div
                  className="h-full rounded-full bg-emerald-400/80"
                  style={{ width: `${Math.min(100, pt.avg_stability_gain * 10)}%` }}
                />
              </div>
              <span className="w-16 text-right tabular-nums text-slate-300">
                +{pt.avg_stability_gain}d ΔS
              </span>
              <span className="w-12 text-right tabular-nums text-slate-500">
                {pt.review_count} rev
              </span>
            </div>
          ))}
          <div className="flex justify-between pt-1 text-[11px] text-slate-600">
            <span>Retrievability (R)</span>
            <span>Stability gain per review</span>
          </div>
        </div>
      )}
    </Section>
  )
}

// ── 4. Metacognitive Calibration & Brier Score ────────────────────────────────

function MetacognitiveCalibration({ metacognition }: { metacognition: LearningAnalytics['metacognition'] }) {
  const curve = metacognition.calibration_curve || []

  return (
    <Section
      title="Metacognitive Calibration & Brier Score"
      description="Alignment between pre-recall Judgment of Learning (JOL) and empirical recall."
    >
      <div className="mb-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-lg border border-ink-line bg-ink p-2.5">
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Brier Score</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-slate-100">
            {metacognition.brier_score.toFixed(3)}
          </p>
          <p className="text-[10px] text-slate-500">0.00 = perfect calibration</p>
        </div>
        <div className="rounded-lg border border-ink-line bg-ink p-2.5">
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Overconfidence</p>
          <p
            className={`mt-0.5 text-xl font-semibold tabular-nums ${
              Math.abs(metacognition.overconfidence_index) < 0.08
                ? 'text-emerald-300'
                : metacognition.overconfidence_index > 0
                  ? 'text-rose-300'
                  : 'text-sky-300'
            }`}
          >
            {metacognition.overconfidence_index > 0 ? '+' : ''}
            {(metacognition.overconfidence_index * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] text-slate-500">predicted vs actual</p>
        </div>
        <div className="rounded-lg border border-ink-line bg-ink p-2.5">
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Hypercorrection</p>
          <p className="mt-0.5 text-xl font-semibold tabular-nums text-emerald-300">
            {Math.round(metacognition.hypercorrection_retention * 100)}%
          </p>
          <p className="text-[10px] text-slate-500">subsequent recall on errors</p>
        </div>
      </div>

      <p className="mb-3 text-xs text-slate-400">{metacognition.calibration_verdict}</p>

      <div className="space-y-2">
        {curve.map((b) => {
          const obsPct = Math.round(b.observed_accuracy * 100)
          const predPct = Math.round(b.predicted_prob * 100)
          return (
            <div key={b.confidence_level} className="flex items-center gap-3 text-xs">
              <span className="w-24 text-slate-400">{b.label}</span>
              <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-ink-line">
                <div
                  className="h-full rounded-full bg-sky-400/80"
                  style={{ width: `${obsPct}%` }}
                />
                {/* Predicted tick mark */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-rose-400"
                  style={{ left: `${predPct}%` }}
                  title={`Predicted: ${predPct}%`}
                />
              </div>
              <span className="w-12 text-right tabular-nums text-slate-200">{obsPct}%</span>
              <span className="w-12 text-right tabular-nums text-slate-500">({b.review_count})</span>
            </div>
          )
        })}
        <div className="flex justify-between pt-1 text-[11px] text-slate-600">
          <span>Confidence tier</span>
          <span>Blue bar: observed recall · Red line: expected probability</span>
        </div>
      </div>
    </Section>
  )
}

// ── 5. Item Discrimination (r_pb) Diagnostic Triage ──────────────────────────

function ItemDiscriminationTriage({ discrimination }: { discrimination: LearningAnalytics['item_discrimination'] }) {
  const [tab, setTab] = useState<'ambiguous' | 'high'>('ambiguous')
  const ambiguous = discrimination.ambiguous_cards || []
  const high = discrimination.high_discrimination || []
  const currentList = tab === 'ambiguous' ? ambiguous : high

  return (
    <Section
      title={`Psychometric Item Discrimination (${discrimination.overall_deck_r.toFixed(2)} r_pb)`}
      description="Item Response Theory point-biserial correlation: separates concept benchmarks from ambiguous cards."
      actions={
        <div className="flex gap-1.5 text-xs">
          <button
            onClick={() => setTab('ambiguous')}
            className={`btn px-2.5 py-1 ${tab === 'ambiguous' ? 'btn-primary' : ''}`}
          >
            Ambiguous cards ({ambiguous.length})
          </button>
          <button
            onClick={() => setTab('high')}
            className={`btn px-2.5 py-1 ${tab === 'high' ? 'btn-primary' : ''}`}
          >
            High discrimination ({high.length})
          </button>
        </div>
      }
    >
      {currentList.length === 0 ? (
        <Empty title={tab === 'ambiguous' ? 'No ambiguous cards detected!' : 'No items analyzed yet.'} />
      ) : (
        <div className="space-y-2.5">
          {currentList.map((c: DiscriminatedCard) => (
            <div key={c.card_id} className="rounded-lg border border-ink-line bg-ink/60 p-3 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`chip ${
                      c.classification === 'high'
                        ? 'border-emerald-500/40 text-emerald-300'
                        : 'border-rose-500/40 text-rose-300'
                    }`}
                  >
                    r_pb: {c.point_biserial_r.toFixed(2)}
                  </span>
                  <span className="chip">{Math.round(c.pass_rate * 100)}% pass rate</span>
                  {c.deck_name && <span className="chip text-slate-500">{c.deck_name}</span>}
                </div>
                <span className="text-slate-500">{c.review_count} reviews</span>
              </div>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <div className="rounded border border-ink-line bg-ink p-2 text-slate-200">
                  <span className="text-[10px] uppercase text-slate-500">Front: </span>
                  {c.front}
                </div>
                <div className="rounded border border-ink-line bg-ink p-2 text-slate-400">
                  <span className="text-[10px] uppercase text-slate-500">Back: </span>
                  {c.back}
                </div>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">{c.rationale}</p>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

// ── 6. EWMA Skill Health & Wald's SPRT Gating ─────────────────────────────────

function EWMAMasteryAndSPRT({
  ewmaScores,
  sprtVerdicts,
}: {
  ewmaScores: LearningAnalytics['ewma_mastery']
  sprtVerdicts: LearningAnalytics['sprt_gating']
}) {
  return (
    <Section
      title="Knowledge Tree Mastery: EWMA & Wald's SPRT"
      description="Recency-weighted mastery health bars (EWMA) and sequential hypothesis testing for prerequisite unlocking (SPRT)."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        {/* EWMA Health Bars */}
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            EWMA Skill Health Meter (λ = 0.25)
          </h3>
          {ewmaScores.length === 0 ? (
            <Empty title="No topics reviewed in the tree yet." />
          ) : (
            <div className="space-y-2">
              {ewmaScores.slice(0, 8).map((s) => (
                <div key={s.node_id} className="flex items-center gap-3 text-xs">
                  <span className="w-32 truncate text-slate-300" title={s.title}>
                    {s.title}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-line">
                    <div
                      className={`h-full rounded-full ${
                        s.ewma_pct >= 85
                          ? 'bg-emerald-400/80'
                          : s.ewma_pct >= 65
                            ? 'bg-sky-400/80'
                            : 'bg-amber-400/80'
                      }`}
                      style={{ width: `${s.ewma_pct}%` }}
                    />
                  </div>
                  <span className="w-12 text-right tabular-nums text-slate-200">
                    {s.ewma_pct.toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Wald's SPRT Gating Verdicts */}
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Wald's SPRT Prerequisite Verdicts
          </h3>
          {sprtVerdicts.length === 0 ? (
            <Empty title="No prerequisite gates configured. Set prerequisites in the Knowledge Tree." />
          ) : (
            <div className="space-y-2">
              {sprtVerdicts.map((v) => (
                <div
                  key={v.node_id}
                  className="flex items-center justify-between rounded-lg border border-ink-line bg-ink p-2.5 text-xs"
                >
                  <div className="min-w-0 flex-1 pr-2">
                    <p className="truncate font-medium text-slate-200">{v.title}</p>
                    <p className="text-[10px] text-slate-500">
                      LLR: {v.log_likelihood_ratio.toFixed(2)} / Bound: [{v.threshold_lower}, {v.threshold_upper}] · {v.cards_evaluated} trials
                    </p>
                  </div>
                  <span
                    className={`chip font-semibold ${
                      v.verdict === 'mastered'
                        ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'
                        : v.verdict === 'unmastered'
                          ? 'border-rose-500/40 text-rose-300 bg-rose-500/10'
                          : 'border-amber-500/40 text-amber-300 bg-amber-500/10'
                    }`}
                  >
                    {v.verdict === 'mastered'
                      ? '🏆 Mastered'
                      : v.verdict === 'unmastered'
                        ? '🛑 Unmastered'
                        : '⏳ Testing'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Section>
  )
}

// ── Standard Helpers ─────────────────────────────────────────────────────────

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

function TimeBank({ bank }: { bank: Bank }) {
  const empty = bank.total_seconds === 0 && bank.recent.length === 0
  return (
    <Section
      title="Time bank"
      description="Time earned back by finishing a block's card target early. Start a block from the Review page."
    >
      {empty ? (
        <Empty title="No banked time yet.">
          Start a timed block with a card target and finish it early — whatever's left on the
          clock lands here.
        </Empty>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Today</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-300">
                {formatBanked(bank.today_seconds)}
              </p>
              <p className="mt-0.5 text-xs text-slate-600">
                {bank.goals_met_today}/{bank.sessions_today} targets met
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Last 7 days</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
                {formatBanked(bank.week_seconds)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">All time</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
                {formatBanked(bank.total_seconds)}
              </p>
            </div>
          </div>

          {bank.recent.length > 0 && (
            <div className="mt-5 space-y-1.5">
              <p className="label">Recent blocks</p>
              {bank.recent.map((s) => (
                <div
                  key={s.id}
                  className="rounded-lg border border-ink-line px-3 py-2 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <span className="text-slate-300">
                        {s.focus_goal || <span className="text-slate-600">no stated goal</span>}
                      </span>
                      <span className="ml-2 text-slate-600">
                        {new Date(s.started_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="chip">
                        {s.cards_reviewed}
                        {s.goal_cards > 0 && `/${s.goal_cards}`} cards
                      </span>
                      <span className="chip">{formatBanked(s.active_seconds)} active</span>
                      {s.banked_seconds > 0 ? (
                        <span className="chip border-emerald-500/40 text-emerald-300">
                          +{formatBanked(s.banked_seconds)}
                        </span>
                      ) : (
                        <span className="chip text-slate-600">—</span>
                      )}
                    </div>
                  </div>
                  {(s.distraction || s.next_time_plan) && (
                    <div className="mt-1.5 space-y-0.5 border-t border-ink-line/60 pt-1.5 text-slate-500">
                      {s.distraction && <p>Distracted by: {s.distraction}</p>}
                      {s.next_time_plan && <p>Next time: {s.next_time_plan}</p>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </Section>
  )
}

function Velocity({ velocity }: { velocity: Record<string, number> }) {
  const activeHours = velocity.active_hours ?? 0
  const inBlocks = Math.round(velocity.mastered ?? 0)
  const total = Math.round(velocity.mastered_total ?? 0)
  const untimed = Math.max(0, total - inBlocks)

  return (
    <Section
      title="Velocity"
      description="Concepts mastered per active hour — efficiency, not time spent."
    >
      {activeHours > 0 ? (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Per hour</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-sky-300">
                {(velocity.per_hour ?? 0).toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Mastered in blocks
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
                {inBlocks}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Active hours</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
                {activeHours.toFixed(1)}
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-600">
            {total} mastered in total
            {untimed > 0 && (
              <>
                {' '}
                — {untimed} of those outside a timed block, so they don't count toward the rate.
              </>
            )}
          </p>
        </>
      ) : (
        <Empty title="No timed blocks yet.">
          Velocity is measured against the Time Bank — start a timed block on Review so there's
          active time to divide mastered cards by.
          {total > 0 && <> You've mastered {total} so far outside timed blocks.</>}
        </Empty>
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
