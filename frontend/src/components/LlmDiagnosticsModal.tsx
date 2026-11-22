import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError, api } from '../api/client'
import type { LlmDiagnosticsResponse, LlmEngineStatusResponse, LlmPingResponse, VramMetrics } from '../api/types'
import { NativeDialog } from './NativeDialog'
import {
  buildDiagnosticReport,
  captureChromeSnapshot,
  clearLlmTraces,
  isThinkingModel,
  useLlmTraces,
  type LlmTraceEntry,
} from '../utils/llmDiagnostics'

export interface LlmDiagnosticsModalProps {
  isOpen: boolean
  onClose: () => void
  activeModel: string
  initialFocusTraceId?: string | null
  onSelectModel?: (model: string) => void
}

type DiagTab = 'traces' | 'engine' | 'playbook'

function formatBytesGb(bytes: number): string {
  if (!bytes || bytes <= 0) return '0.0 GB'
  return `${(bytes / 1e9).toFixed(2)} GB`
}

function formatDuration(ms: number | null): string {
  if (ms == null) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatTime(ts: number): string {
  try {
    return new Date(ts).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return ''
  }
}

export function LlmDiagnosticsModal({
  isOpen,
  onClose,
  activeModel,
  initialFocusTraceId = null,
  onSelectModel,
}: LlmDiagnosticsModalProps) {
  const traces = useLlmTraces()
  const [tab, setTab] = useState<DiagTab>('traces')
  const [serverDiag, setServerDiag] = useState<LlmDiagnosticsResponse | null>(null)
  const [fallbackStatus, setFallbackStatus] = useState<LlmEngineStatusResponse | null>(null)
  const [fallbackVram, setFallbackVram] = useState<VramMetrics | null>(null)
  const [probing, setProbing] = useState(false)
  const [probeError, setProbeError] = useState<string | null>(null)
  const [pingResult, setPingResult] = useState<LlmPingResponse | null>(null)
  const [pinging, setPinging] = useState(false)
  const [pingError, setPingError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(initialFocusTraceId)
  const [copiedReport, setCopiedReport] = useState(false)
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null)
  const [nowTick, setNowTick] = useState(() => Date.now())

  useEffect(() => {
    if (initialFocusTraceId) {
      setExpandedId(initialFocusTraceId)
      setTab('traces')
    }
  }, [initialFocusTraceId])

  // Live ticker while modal is open and any request is pending
  useEffect(() => {
    if (!isOpen || traces.activeCount === 0) return
    const timer = window.setInterval(() => setNowTick(Date.now()), 200)
    return () => window.clearInterval(timer)
  }, [isOpen, traces.activeCount])

  const runProbe = useCallback(async () => {
    setProbing(true)
    setProbeError(null)
    try {
      const diag = await api.llmDiagnostics()
      setServerDiag(diag)
      setFallbackStatus(null)
      setFallbackVram(null)
    } catch (err: unknown) {
      // External FastAPI backends may not implement /api/llm/diagnostics yet —
      // gracefully fall back to /api/llm/status + /api/llm/vram so the inspector always works.
      const is404 = err instanceof ApiError && err.status === 404
      if (is404) {
        try {
          const [st, vr] = await Promise.all([
            api.llmStatus(),
            api.vramStatus(activeModel).catch(() => null),
          ])
          setFallbackStatus(st)
          setFallbackVram(vr)
          setServerDiag({
            checked_at: new Date().toISOString(),
            backend_mode: 'external',
            active_model: st.model || activeModel,
            ollama: {
              reachable: Boolean(st.connected),
              base_url: st.base_url || 'http://127.0.0.1:11434',
              version: null,
              latency_ms: null,
              error: st.error ?? null,
              loaded_models: [],
              installed_models: st.models_installed ?? [],
            },
            host: {
              platform: 'external-backend',
              cpu_cores: 0,
              total_ram_gb: vr?.capacity_gb ?? 0,
              free_ram_gb: vr?.available_gb ?? 0,
            },
            recent_events: [],
            hints: [
              'Connected to an external backend (using /api/llm/status & /api/llm/vram). Full browser-side request traces are active below.',
            ],
          })
        } catch (fallbackErr: unknown) {
          setProbeError(fallbackErr instanceof Error ? fallbackErr.message : String(fallbackErr))
        }
      } else {
        setProbeError(err instanceof Error ? err.message : String(err))
      }
    } finally {
      setProbing(false)
    }
  }, [activeModel])

  useEffect(() => {
    if (!isOpen) return
    void runProbe()
  }, [isOpen, runProbe])

  const runPing = useCallback(
    async (warmup: boolean) => {
      setPinging(true)
      setPingError(null)
      try {
        const res = await api.llmPing(activeModel, warmup)
        setPingResult(res)
        void runProbe()
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 404) {
          // External backend fallback: measure /api/llm/status latency directly
          const t0 = Date.now()
          try {
            const st = await api.llmStatus()
            const dt = Date.now() - t0
            setPingResult({
              ok: Boolean(st.connected),
              mode: st.provider === 'ollama' ? 'ollama' : 'heuristic',
              model: st.model || activeModel,
              latency_ms: dt,
              ollama_version: null,
              model_loaded: Boolean(st.model_ready),
              gpu_offload_pct: null,
              message: st.connected
                ? `Backend & ${st.provider} responded in ${dt}ms.`
                : `Backend responded in ${dt}ms, but local LLM is not connected (${st.error || 'offline'}).`,
            })
          } catch (innerErr: unknown) {
            setPingError(innerErr instanceof Error ? innerErr.message : String(innerErr))
          }
        } else {
          setPingError(err instanceof Error ? err.message : String(err))
        }
      } finally {
        setPinging(false)
      }
    },
    [activeModel, runProbe],
  )

  const chromeSnapshot = useMemo(
    () => captureChromeSnapshot(traces.activeCount),
    // Refresh snapshot when modal opens, traces update, or probe runs
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isOpen, traces.entries.length, traces.activeCount, probing],
  )

  const thinkingActive = isThinkingModel(activeModel)

  const handleCopyReport = async () => {
    const report = buildDiagnosticReport(traces, serverDiag, activeModel)
    try {
      await navigator.clipboard.writeText(report)
      setCopiedReport(true)
      window.setTimeout(() => setCopiedReport(false), 2000)
    } catch {
      // Clipboard blocked in non-secure context
    }
  }

  const handleCopyCmd = async (cmd: string) => {
    try {
      await navigator.clipboard.writeText(cmd)
      setCopiedCmd(cmd)
      window.setTimeout(() => setCopiedCmd(null), 1600)
    } catch {
      // ignore
    }
  }

  const statusBadge = (entry: LlmTraceEntry) => {
    switch (entry.status) {
      case 'pending':
        return 'border-amber-500/50 bg-amber-500/15 text-amber-200'
      case 'ok':
        return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
      case 'slow':
        return 'border-amber-500/50 bg-amber-500/15 text-amber-300'
      case 'error':
      case 'timeout':
        return 'border-rose-500/50 bg-rose-500/15 text-rose-200'
      case 'aborted':
        return 'border-slate-600 bg-slate-800/80 text-slate-300'
    }
  }

  return (
    <NativeDialog
      open={isOpen}
      onClose={onClose}
      ariaLabel="Local LLM and Chrome Diagnostics"
      className="w-full max-w-4xl rounded-2xl border border-slate-700/80 bg-slate-950 text-slate-100 shadow-2xl overflow-hidden"
    >
      <div className="flex max-h-[88vh] flex-col">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-900/80 px-5 py-3.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-sky-500/40 bg-sky-500/15 text-sky-300">
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </span>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-slate-100 truncate">
                Local LLM &amp; Chrome Diagnostics
              </h2>
              <p className="text-[0.6875rem] text-slate-400 truncate">
                Inspect live Ollama latency, VRAM vs CPU offload, and exact failure reasons
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void runProbe()}
              disabled={probing}
              className="btn text-xs py-1 px-2.5 border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200"
            >
              {probing ? 'Probing…' : 'Run Live Probe'}
            </button>
            <button
              type="button"
              onClick={() => void runPing(true)}
              disabled={pinging}
              className="btn text-xs py-1 px-2.5 border-sky-500/40 bg-sky-500/15 hover:bg-sky-500/25 text-sky-200"
              title="Send a tiny 1-token ping to warm up the active model and measure real latency"
            >
              {pinging ? 'Pinging…' : 'Ping & Warmup'}
            </button>
            <button
              type="button"
              onClick={() => void handleCopyReport()}
              className="btn text-xs py-1 px-2.5 border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-300"
            >
              {copiedReport ? 'Copied JSON' : 'Copy Report'}
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close diagnostics"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Summary Telemetry Tiles */}
        <div className="grid gap-3 border-b border-slate-800 bg-slate-950/90 px-5 py-3.5 md:grid-cols-3">
          {/* Tile 1: Engine / Ollama */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 space-y-1.5">
            <div className="flex items-center justify-between text-[0.6875rem]">
              <span className="font-semibold uppercase tracking-wide text-slate-400">Backend &amp; Ollama</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold border ${
                  serverDiag?.ollama.reachable
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : serverDiag?.backend_mode === 'heuristic'
                    ? 'border-sky-500/40 bg-sky-500/10 text-sky-300'
                    : 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                }`}
              >
                {probing
                  ? 'Checking…'
                  : serverDiag?.ollama.reachable
                  ? `Ollama ${serverDiag.ollama.version ?? 'Connected'}`
                  : serverDiag?.backend_mode === 'heuristic'
                  ? 'Heuristic Mode'
                  : 'Unreachable'}
              </span>
            </div>
            <div className="text-xs font-mono text-slate-200 truncate">
              {serverDiag?.ollama.base_url || fallbackStatus?.base_url || 'http://127.0.0.1:11434'}
            </div>
            <div className="text-[0.6875rem] text-slate-400">
              {serverDiag?.ollama.latency_ms != null
                ? `Probe RTT: ${serverDiag.ollama.latency_ms}ms`
                : serverDiag?.ollama.error
                ? serverDiag.ollama.error
                : fallbackStatus?.error || 'Ready'}
            </div>
          </div>

          {/* Tile 2: Active Model */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 space-y-1.5">
            <div className="flex items-center justify-between text-[0.6875rem]">
              <span className="font-semibold uppercase tracking-wide text-slate-400">Active Grader</span>
              {thinkingActive ? (
                <span className="rounded px-1.5 py-0.5 text-[0.625rem] font-semibold border border-amber-500/40 bg-amber-500/15 text-amber-200">
                  Thinking Model
                </span>
              ) : (
                <span className="rounded px-1.5 py-0.5 text-[0.625rem] font-semibold border border-emerald-500/40 bg-emerald-500/10 text-emerald-300">
                  Direct Output
                </span>
              )}
            </div>
            <div className="text-xs font-mono font-semibold text-slate-100 truncate">{activeModel}</div>
            <div className="text-[0.6875rem] text-slate-400">
              {thinkingActive
                ? 'Qwen 3.5 emits hidden reasoning tokens unless think: false is set.'
                : fallbackVram?.gpu_name
                ? `${fallbackVram.gpu_name} · ${fallbackVram.available_gb != null ? `${fallbackVram.available_gb.toFixed(1)} GB free` : 'VRAM ready'}`
                : 'Low overhead for short recall answers.'}
            </div>
          </div>

          {/* Tile 3: Chrome Environment */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 space-y-1.5">
            <div className="flex items-center justify-between text-[0.6875rem]">
              <span className="font-semibold uppercase tracking-wide text-slate-400">
                {chromeSnapshot.browserLabel}
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold border ${
                  traces.activeCount > 1
                    ? 'border-amber-500/50 bg-amber-500/15 text-amber-200'
                    : chromeSnapshot.online
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : 'border-rose-500/50 bg-rose-500/15 text-rose-200'
                }`}
              >
                {traces.activeCount > 0 ? `${traces.activeCount} in flight` : chromeSnapshot.online ? 'Online' : 'Offline'}
              </span>
            </div>
            <div className="text-xs font-mono text-slate-200">
              Tab: {chromeSnapshot.visibilityState}
              {chromeSnapshot.jsHeapUsedMb != null ? ` · Heap ${chromeSnapshot.jsHeapUsedMb} MB` : ''}
            </div>
            <div className="text-[0.6875rem] text-slate-400">
              {traces.activeCount > 1
                ? 'Multiple LLM requests queued — Ollama serializes calls by default.'
                : 'Press Shift+Esc in Chrome to check GPU Process VRAM usage.'}
            </div>
          </div>
        </div>

        {/* Ping / Probe feedback strip */}
        {(pingResult || pingError || probeError) && (
          <div className="border-b border-slate-800 px-5 py-2.5 text-xs">
            {pingResult && (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-sky-500/30 bg-sky-950/30 px-3 py-2 text-sky-200">
                <span>{pingResult.message}</span>
                <span className="font-mono text-[0.6875rem] text-sky-300">
                  {formatDuration(pingResult.latency_ms)}
                </span>
              </div>
            )}
            {(pingError || probeError) && (
              <div className="mt-1.5 rounded-lg border border-rose-500/40 bg-rose-950/30 px-3 py-2 text-rose-200">
                {pingError || probeError}
              </div>
            )}
          </div>
        )}

        {/* Quick-Switch Warning if Qwen 3.5 is active and onSelectModel is available */}
        {thinkingActive && onSelectModel && (
          <div className="border-b border-slate-800 bg-amber-950/20 px-5 py-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="text-amber-200">
              <strong className="font-semibold">Tip for slow Qwen 3.5 grading:</strong>{' '}
              <code className="font-mono text-amber-100">{activeModel}</code> can stall on short answers while generating hidden thinking tokens. Switching to{' '}
              <code className="font-mono text-amber-100">qwen2.5-coder:7b</code> avoids thinking-token delays.
            </div>
            <button
              type="button"
              onClick={() => {
                onSelectModel('qwen2.5-coder:7b')
                onClose()
              }}
              className="btn text-xs py-1 px-2.5 border-amber-500/50 bg-amber-500/15 hover:bg-amber-500/25 text-amber-100 shrink-0"
            >
              Switch to qwen2.5-coder:7b
            </button>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/40 px-5">
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => setTab('traces')}
              className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition ${
                tab === 'traces'
                  ? 'border-sky-400 text-sky-200'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Request Trace Log ({traces.entries.length})
            </button>
            <button
              type="button"
              onClick={() => setTab('engine')}
              className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition ${
                tab === 'engine'
                  ? 'border-sky-400 text-sky-200'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Loaded Models &amp; Server Events
            </button>
            <button
              type="button"
              onClick={() => setTab('playbook')}
              className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition ${
                tab === 'playbook'
                  ? 'border-sky-400 text-sky-200'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Chrome + Ollama Fix Checklist
            </button>
          </div>
          {tab === 'traces' && traces.entries.length > 0 && (
            <button
              type="button"
              onClick={() => clearLlmTraces()}
              className="text-[0.6875rem] text-slate-400 hover:text-slate-200 underline"
            >
              Clear log
            </button>
          )}
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {tab === 'traces' && (
            <>
              {traces.entries.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-800 px-6 py-10 text-center space-y-2">
                  <p className="text-sm text-slate-300 font-medium">No LLM requests recorded in this tab yet.</p>
                  <p className="text-xs text-slate-500">
                    Submit an answer, open Socratic Guide, or click &ldquo;Ping &amp; Warmup&rdquo; above to capture live timing and failure telemetry.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {traces.entries.map((entry) => {
                    const isExpanded = expandedId === entry.id
                    const liveDuration =
                      entry.status === 'pending' ? Math.max(0, nowTick - entry.startedAt) : entry.durationMs
                    return (
                      <div
                        key={entry.id}
                        className={`rounded-xl border transition ${
                          entry.status === 'error' || entry.status === 'timeout'
                            ? 'border-rose-500/40 bg-rose-950/15'
                            : entry.status === 'slow' || entry.status === 'pending'
                            ? 'border-amber-500/40 bg-amber-950/15'
                            : 'border-slate-800 bg-slate-900/50'
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                          className="w-full px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-2 text-left"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className={`rounded px-1.5 py-0.5 text-[0.625rem] font-mono font-bold uppercase border ${statusBadge(entry)}`}
                            >
                              {entry.status === 'pending' ? 'RUNNING' : entry.status}
                            </span>
                            <span className="text-xs font-semibold text-slate-100">{entry.operation}</span>
                            {(entry.responseModelUsed || entry.model) && (
                              <span className="text-[0.6875rem] font-mono text-slate-400 truncate max-w-[180px]">
                                {entry.responseModelUsed || entry.model}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-xs font-mono">
                            {entry.httpStatus != null && (
                              <span
                                className={
                                  entry.httpStatus >= 400 ? 'text-rose-300' : 'text-slate-400'
                                }
                              >
                                HTTP {entry.httpStatus}
                              </span>
                            )}
                            <span
                              className={
                                (liveDuration ?? 0) >= 20_000
                                  ? 'text-rose-300 font-bold'
                                  : (liveDuration ?? 0) >= 8_000
                                  ? 'text-amber-300 font-semibold'
                                  : 'text-slate-200'
                              }
                            >
                              {formatDuration(liveDuration)}
                            </span>
                            <span className="text-[0.6875rem] text-slate-500">{formatTime(entry.startedAt)}</span>
                            <span className="text-slate-500">{isExpanded ? '▴' : '▾'}</span>
                          </div>
                        </button>

                        {entry.errorMessage && !isExpanded && (
                          <div className="px-3.5 pb-2.5 text-xs text-rose-200/90 truncate">
                            {entry.errorMessage}
                            {entry.diagnosis ? ` — ${entry.diagnosis.title}` : ''}
                          </div>
                        )}

                        {isExpanded && (
                          <div className="border-t border-slate-800/80 px-3.5 py-3 space-y-3 text-xs">
                            <div className="grid gap-2 sm:grid-cols-2 text-[0.6875rem]">
                              <div>
                                <span className="text-slate-500">Endpoint: </span>
                                <code className="font-mono text-slate-300">{entry.endpoint}</code>
                              </div>
                              <div>
                                <span className="text-slate-500">Chrome context: </span>
                                <span className="font-mono text-slate-300">
                                  tab={entry.chromeContext.visibilityState}, inFlight={entry.chromeContext.inFlightCount}
                                  {entry.chromeContext.jsHeapUsedMb != null
                                    ? `, heap=${entry.chromeContext.jsHeapUsedMb}MB`
                                    : ''}
                                </span>
                              </div>
                            </div>

                            {entry.rawDetail && (
                              <div className="rounded-lg border border-slate-800 bg-black/50 p-2.5 font-mono text-[0.6875rem] text-rose-200 break-words whitespace-pre-wrap">
                                {entry.rawDetail}
                              </div>
                            )}

                            {entry.diagnosis && (
                              <div
                                className={`rounded-lg border p-3 space-y-2 ${
                                  entry.diagnosis.severity === 'error'
                                    ? 'border-rose-500/40 bg-rose-950/30'
                                    : entry.diagnosis.severity === 'warn'
                                    ? 'border-amber-500/40 bg-amber-950/30'
                                    : 'border-slate-700 bg-slate-900/70'
                                }`}
                              >
                                <div className="font-semibold text-slate-100">{entry.diagnosis.title}</div>
                                <p className="text-slate-300 leading-relaxed">{entry.diagnosis.summary}</p>
                                {entry.diagnosis.likelyCauses.length > 0 && (
                                  <div>
                                    <div className="text-[0.6875rem] font-semibold uppercase tracking-wide text-slate-400 mb-1">
                                      Likely Causes
                                    </div>
                                    <ul className="list-disc pl-4 space-y-1 text-slate-300">
                                      {entry.diagnosis.likelyCauses.map((c, idx) => (
                                        <li key={idx}>{c}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {entry.diagnosis.suggestedFixes.length > 0 && (
                                  <div>
                                    <div className="text-[0.6875rem] font-semibold uppercase tracking-wide text-emerald-300 mb-1">
                                      What to Try
                                    </div>
                                    <ul className="list-disc pl-4 space-y-1 text-emerald-200/90">
                                      {entry.diagnosis.suggestedFixes.map((f, idx) => (
                                        <li key={idx}>{f}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </>
          )}

          {tab === 'engine' && (
            <div className="space-y-4">
              {serverDiag && serverDiag.hints.length > 0 && (
                <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-3.5 space-y-1.5 text-xs">
                  <div className="font-semibold text-sky-200">Live Observations</div>
                  <ul className="list-disc pl-4 space-y-1 text-slate-300">
                    {serverDiag.hints.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Models Currently Warm in Ollama Memory (/api/ps)
                </h3>
                {serverDiag?.ollama.loaded_models && serverDiag.ollama.loaded_models.length > 0 ? (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {serverDiag.ollama.loaded_models.map((m) => (
                      <div
                        key={m.name}
                        className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 space-y-1.5 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono font-semibold text-slate-100">{m.name}</span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[0.625rem] font-mono font-bold border ${
                              m.gpu_offload_pct >= 99
                                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                                : 'border-amber-500/50 bg-amber-500/15 text-amber-200'
                            }`}
                          >
                            {m.gpu_offload_pct}% GPU / {100 - m.gpu_offload_pct}% CPU
                          </span>
                        </div>
                        <div className="text-[0.6875rem] text-slate-400 font-mono">
                          VRAM: {formatBytesGb(m.size_vram_bytes)} / Total: {formatBytesGb(m.size_bytes)}
                        </div>
                        {m.expires_at && (
                          <div className="text-[0.6875rem] text-slate-500">
                            Unloads at: {new Date(m.expires_at).toLocaleTimeString()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="rounded-xl border border-dashed border-slate-800 px-4 py-4 text-xs text-slate-400">
                    {serverDiag?.ollama.reachable
                      ? 'No model is currently resident in VRAM. Click "Ping & Warmup" above to load the active model before reviewing.'
                      : 'Ollama /api/ps is only populated when a local Ollama daemon is reachable from the active backend.'}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Recent Backend Grading Events
                </h3>
                {serverDiag?.recent_events && serverDiag.recent_events.length > 0 ? (
                  <div className="divide-y divide-slate-800 rounded-xl border border-slate-800 bg-slate-900/40 text-xs">
                    {serverDiag.recent_events.map((ev) => (
                      <div key={ev.id} className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{ev.operation}</span>
                          <span className="font-mono text-[0.6875rem] text-slate-400">{ev.model}</span>
                          {ev.detail && <span className="text-[0.6875rem] text-slate-500">({ev.detail})</span>}
                        </div>
                        <div className="flex items-center gap-3 font-mono text-[0.6875rem]">
                          <span className={ev.status === 'error' ? 'text-rose-300' : 'text-emerald-300'}>
                            {formatDuration(ev.duration_ms)}
                          </span>
                          <span className="text-slate-500">
                            {new Date(ev.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No server-side events recorded yet.</p>
                )}
              </div>
            </div>
          )}

          {tab === 'playbook' && (
            <div className="space-y-3 text-xs">
              <div className="rounded-xl border border-amber-500/35 bg-amber-950/20 p-3.5 space-y-1.5">
                <div className="font-semibold text-amber-200">
                  1. Why &ldquo;Ollama generation failed:&rdquo; appears blank after a slow wait
                </div>
                <p className="text-slate-300 leading-relaxed">
                  In local Python/FastAPI + Ollama setups, when Ollama takes longer than the backend&apos;s HTTP read timeout,{' '}
                  <code className="font-mono text-amber-100">httpx.ReadTimeout</code> has an empty string representation — producing literally{' '}
                  <code className="font-mono text-rose-200">Ollama generation failed:</code> with nothing after the colon.
                </p>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-2">
                <div className="font-semibold text-slate-100">
                  2. Check if Chrome is forcing Ollama off your GPU onto CPU RAM
                </div>
                <p className="text-slate-300 leading-relaxed">
                  Chrome&apos;s hardware-accelerated GPU Process (especially with YouTube, PDFs, or 15+ tabs) shares the same GPU VRAM as Ollama. If VRAM fills up, Ollama silently puts 30–60% of layers on CPU RAM, making every card 10&times; slower.
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <code className="rounded bg-black/60 border border-slate-800 px-2.5 py-1 font-mono text-emerald-300">
                    ollama ps
                  </code>
                  <button
                    type="button"
                    onClick={() => void handleCopyCmd('ollama ps')}
                    className="btn text-[0.6875rem] py-0.5 px-2"
                  >
                    {copiedCmd === 'ollama ps' ? 'Copied' : 'Copy'}
                  </button>
                  <span className="text-slate-400">
                    Look at the <strong>PROCESSOR</strong> column — it should say <strong>100% GPU</strong>. Also press <kbd className="rounded border border-slate-700 bg-slate-800 px-1 py-0.5 font-mono text-[0.625rem]">Shift+Esc</kbd> in Chrome to check GPU Process memory.
                  </span>
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-2">
                <div className="font-semibold text-slate-100">
                  3. Qwen 3.5 hidden thinking-token runaway
                </div>
                <p className="text-slate-300 leading-relaxed">
                  <code className="font-mono text-slate-200">qwen3.5:4b</code> and <code className="font-mono text-slate-200">qwen3.5:9b</code> enable internal chain-of-thought by default in Ollama. Even a 1-word answer like <code className="font-mono text-slate-200">falso</code> can trigger hundreds of hidden reasoning tokens before the JSON response starts. Switch to <code className="font-mono text-emerald-300">qwen2.5-coder:7b</code> or send <code className="font-mono text-sky-300">&quot;think&quot;: false</code> in your Ollama API payload.
                </p>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-2">
                <div className="font-semibold text-slate-100">
                  4. Stop 5-minute cold-load pauses between cards
                </div>
                <p className="text-slate-300 leading-relaxed">
                  By default Ollama evicts models from VRAM after 5 minutes of inactivity. Start Ollama with a longer keep-alive window so weights stay hot during a full study block:
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <code className="rounded bg-black/60 border border-slate-800 px-2.5 py-1 font-mono text-emerald-300">
                    OLLAMA_KEEP_ALIVE=30m ollama serve
                  </code>
                  <button
                    type="button"
                    onClick={() => void handleCopyCmd('OLLAMA_KEEP_ALIVE=30m ollama serve')}
                    className="btn text-[0.6875rem] py-0.5 px-2"
                  >
                    {copiedCmd === 'OLLAMA_KEEP_ALIVE=30m ollama serve' ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </NativeDialog>
  )
}
