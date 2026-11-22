import { useSyncExternalStore } from 'react'
import type { LlmDiagnosticsResponse } from '../api/types'

export type LlmTraceStatus = 'pending' | 'ok' | 'slow' | 'error' | 'aborted' | 'timeout'

export interface LlmChromeSnapshot {
  visibilityState: string
  online: boolean
  inFlightCount: number
  hardwareConcurrency: number | null
  deviceMemoryGb: number | null
  jsHeapUsedMb: number | null
  jsHeapLimitMb: number | null
  browserLabel: string
}

export type LlmDiagnosisCode =
  | 'empty_ollama_error'
  | 'qwen35_thinking_stall'
  | 'timeout'
  | 'cold_load_or_vram_swap'
  | 'concurrent_queue_contention'
  | 'background_tab_throttled'
  | 'network_error'
  | 'server_5xx'
  | 'aborted'
  | 'slow_response'
  | 'ok'

export interface LlmDiagnosis {
  code: LlmDiagnosisCode
  severity: 'info' | 'warn' | 'error'
  title: string
  summary: string
  likelyCauses: string[]
  suggestedFixes: string[]
}

export interface LlmTraceEntry {
  id: string
  operation: string
  endpoint: string
  model: string | null
  startedAt: number
  endedAt: number | null
  durationMs: number | null
  status: LlmTraceStatus
  httpStatus: number | null
  errorMessage: string | null
  rawDetail: string | null
  responseModelUsed: string | null
  degradedReason: string | null
  chromeContext: LlmChromeSnapshot
  diagnosis: LlmDiagnosis | null
}

export interface LlmTraceSnapshot {
  entries: LlmTraceEntry[]
  activeCount: number
  lastFailure: LlmTraceEntry | null
  lastSlow: LlmTraceEntry | null
}

const MAX_TRACE_ENTRIES = 40
export const SLOW_LLM_THRESHOLD_MS = 8_000
export const VERY_SLOW_LLM_THRESHOLD_MS = 20_000

let entries: LlmTraceEntry[] = []
let seq = 0
const listeners = new Set<() => void>()

let cachedSnapshot: LlmTraceSnapshot = {
  entries: [],
  activeCount: 0,
  lastFailure: null,
  lastSlow: null,
}

function rebuildSnapshot() {
  const activeCount = entries.filter((e) => e.status === 'pending').length
  const lastFailure = entries.find((e) => e.status === 'error' || e.status === 'timeout') ?? null
  const lastSlow = entries.find((e) => e.status === 'slow') ?? null
  cachedSnapshot = {
    entries: [...entries],
    activeCount,
    lastFailure,
    lastSlow,
  }
}

function emit() {
  rebuildSnapshot()
  for (const listener of listeners) {
    listener()
  }
}

export function captureChromeSnapshot(inFlightCount = 0): LlmChromeSnapshot {
  const hasDoc = typeof document !== 'undefined'
  const hasNav = typeof navigator !== 'undefined'
  const hasPerf = typeof performance !== 'undefined'

  const navAny = hasNav ? (navigator as Navigator & { deviceMemory?: number }) : null
  const perfAny = hasPerf
    ? (performance as Performance & {
        memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number }
      })
    : null

  const ua = hasNav ? navigator.userAgent || '' : ''
  let browserLabel = 'Browser'
  if (/Edg\//.test(ua)) browserLabel = 'Edge (Chromium)'
  else if (/Chrome\//.test(ua)) browserLabel = 'Google Chrome'
  else if (/Firefox\//.test(ua)) browserLabel = 'Firefox'
  else if (/Safari\//.test(ua)) browserLabel = 'Safari'

  return {
    visibilityState: hasDoc ? document.visibilityState : 'unknown',
    online: hasNav ? navigator.onLine : true,
    inFlightCount,
    hardwareConcurrency: hasNav && typeof navigator.hardwareConcurrency === 'number'
      ? navigator.hardwareConcurrency
      : null,
    deviceMemoryGb: navAny && typeof navAny.deviceMemory === 'number' ? navAny.deviceMemory : null,
    jsHeapUsedMb: perfAny?.memory
      ? Math.round(perfAny.memory.usedJSHeapSize / (1024 * 1024))
      : null,
    jsHeapLimitMb: perfAny?.memory
      ? Math.round(perfAny.memory.jsHeapSizeLimit / (1024 * 1024))
      : null,
    browserLabel,
  }
}

export function isThinkingModel(model: string | null | undefined): boolean {
  if (!model) return false
  const lower = model.toLowerCase()
  return lower.includes('qwen3') || lower.includes('deepseek-r1') || lower.includes('qwq')
}

export function isEmptyOllamaError(message: string | null | undefined): boolean {
  if (!message) return false
  return /^ollama\s+generation\s+failed\s*:?\s*$/i.test(message.trim())
}

export function diagnoseLlmTrace(entry: Pick<
  LlmTraceEntry,
  'model' | 'durationMs' | 'status' | 'httpStatus' | 'errorMessage' | 'rawDetail' | 'chromeContext' | 'degradedReason'
>): LlmDiagnosis {
  const durationMs = entry.durationMs ?? 0
  const durationSec = (durationMs / 1000).toFixed(1)
  const msg = (entry.errorMessage || entry.rawDetail || '').trim()
  const lowerMsg = msg.toLowerCase()
  const thinkingModel = isThinkingModel(entry.model)

  if (entry.status === 'aborted') {
    return {
      code: 'aborted',
      severity: 'info',
      title: 'Request cancelled',
      summary: `Cancelled after ${durationSec}s before the model finished responding.`,
      likelyCauses: ['You cancelled the request, revealed the answer, or switched cards/models mid-generation.'],
      suggestedFixes: ['Submit again or switch to a lighter/faster model if this model keeps stalling.'],
    }
  }

  if (entry.status === 'error' || entry.status === 'timeout') {
    if (isEmptyOllamaError(msg)) {
      return {
        code: 'empty_ollama_error',
        severity: 'error',
        title: 'Ollama timed out or dropped the connection with no error body',
        summary: `The backend reported "${msg}" after ${durationSec}s${entry.httpStatus ? ` (HTTP ${entry.httpStatus})` : ''}. In Python/Ollama backends, an empty message after the colon almost always means httpx.ReadTimeout or a dropped local Ollama stream.`,
        likelyCauses: [
          thinkingModel
            ? `${entry.model} enables hidden thinking tokens by default in Ollama, which can stall even a 1-word answer past the HTTP read timeout.`
            : 'Ollama took longer than the backend HTTP timeout to finish generating tokens.',
          'GPU VRAM contention: Chrome hardware acceleration + open tabs can force Ollama to spill layers onto CPU RAM, dropping speed 10x.',
          'Model cold-load: Ollama unloads models after 5 minutes of idle time (default OLLAMA_KEEP_ALIVE=5m) and had to reload weights from disk.',
        ],
        suggestedFixes: [
          thinkingModel
            ? 'Switch to qwen2.5-coder:7b (no thinking-token overhead) or ensure your backend sends think: false to Ollama.'
            : 'Run `ollama ps` in your terminal to verify 100% GPU offload (if you see CPU%, close GPU-heavy Chrome tabs).',
          'Set OLLAMA_KEEP_ALIVE=30m before starting Ollama so the model stays warm in VRAM between cards.',
          'Click "Show answer" anytime to self-grade without waiting on the local model.',
        ],
      }
    }

    if (
      entry.status === 'timeout' ||
      lowerMsg.includes('timeout') ||
      lowerMsg.includes('timed out') ||
      entry.httpStatus === 504 ||
      entry.httpStatus === 408
    ) {
      return {
        code: 'timeout',
        severity: 'error',
        title: `Local LLM timed out (${durationSec}s)`,
        summary: `The request waited ${durationSec}s without a completed response${entry.model ? ` from ${entry.model}` : ''}.`,
        likelyCauses: [
          thinkingModel
            ? `${entry.model} may be spending tens of seconds emitting hidden <think> reasoning tokens.`
            : 'Inference speed dropped below the request timeout (often due to CPU spillover or disk cold-loading).',
          entry.chromeContext.inFlightCount > 1
            ? `${entry.chromeContext.inFlightCount} LLM requests ran concurrently; local Ollama serializes requests by default.`
            : 'Chrome GPU memory usage may have pushed Ollama partially onto system RAM.',
        ],
        suggestedFixes: [
          'Check `ollama ps` in a terminal to see GPU vs CPU split and whether the model is still loaded.',
          'Avoid clicking Submit multiple times or opening Guide/Lexicon while a grade is already in flight.',
          'Press Shift+Esc in Chrome to check the GPU Process memory and close heavy video/WebGL tabs.',
        ],
      }
    }

    if (
      lowerMsg.includes('failed to fetch') ||
      lowerMsg.includes('networkerror') ||
      lowerMsg.includes('econnrefused') ||
      !entry.chromeContext.online
    ) {
      return {
        code: 'network_error',
        severity: 'error',
        title: 'Could not reach the backend / local LLM server',
        summary: !entry.chromeContext.online
          ? 'Chrome reports the browser is offline.'
          : `The browser network request failed after ${durationSec}s (${msg || 'network error'}).`,
        likelyCauses: [
          'The local backend server or Ollama daemon stopped, restarted, or crashed under memory pressure.',
          'Chrome dropped a long-idle localhost connection or a Vite/proxy socket reset.',
        ],
        suggestedFixes: [
          'Click "Run Live Probe" below to verify whether the backend and Ollama respond.',
          'Verify `ollama serve` and your local backend process are still running in your terminal.',
        ],
      }
    }

    if (entry.httpStatus && entry.httpStatus >= 500) {
      return {
        code: 'server_5xx',
        severity: 'error',
        title: `Backend returned HTTP ${entry.httpStatus} after ${durationSec}s`,
        summary: msg || `Server error (${entry.httpStatus}) while running ${entry.model || 'local LLM'}.`,
        likelyCauses: [
          'Ollama runner crashed (OOM / VRAM exhaustion) or returned malformed output.',
          thinkingModel
            ? `${entry.model} may have timed out or exceeded max tokens inside thinking tags.`
            : 'Local model runner hit a resource or timeout limit.',
        ],
        suggestedFixes: [
          'Check the terminal running Ollama / FastAPI for the stack trace or OOM message.',
          'Try a smaller model or close GPU-intensive Chrome tabs to free VRAM.',
        ],
      }
    }

    return {
      code: 'server_5xx',
      severity: 'error',
      title: `LLM request failed (${durationSec}s)`,
      summary: msg || 'The model request did not complete.',
      likelyCauses: ['The backend or local Ollama server rejected or failed the generation call.'],
      suggestedFixes: ['Inspect the raw detail below and run a Live Probe to check Ollama health.'],
    }
  }

  // Completed successfully, check latency & warnings
  if (durationMs >= SLOW_LLM_THRESHOLD_MS) {
    if (entry.chromeContext.inFlightCount > 1) {
      return {
        code: 'concurrent_queue_contention',
        severity: 'warn',
        title: `Slow response (${durationSec}s) — concurrent LLM queue`,
        summary: `${entry.chromeContext.inFlightCount} LLM requests were active simultaneously. Local Ollama processes requests sequentially by default.`,
        likelyCauses: [
          'Another LLM call (Lesson, Lexicon auto-extract, or Guide) was running at the same time.',
        ],
        suggestedFixes: [
          'Wait for one LLM action to finish before triggering another, or set OLLAMA_NUM_PARALLEL=2 if you have spare VRAM.',
        ],
      }
    }

    if (entry.chromeContext.visibilityState !== 'visible') {
      return {
        code: 'background_tab_throttled',
        severity: 'warn',
        title: `Slow response (${durationSec}s) — Chrome background tab`,
        summary: 'This tab was hidden/backgrounded while waiting; Chrome throttles background tab timers and network callbacks.',
        likelyCauses: ['Switching away from the Chrome tab delayed UI updates or coincided with GPU deprioritization.'],
        suggestedFixes: ['Keep the review tab active while grading, or disable Memory Saver for localhost in Chrome settings.'],
      }
    }

    if (thinkingModel) {
      return {
        code: 'qwen35_thinking_stall',
        severity: 'warn',
        title: `Slow ${entry.model} response (${durationSec}s)`,
        summary: `${entry.model} took ${durationSec}s. Qwen 3 / 3.5 models generate internal reasoning tokens before answering unless thinking mode is disabled.`,
        likelyCauses: [
          'Ollama defaults to thinking mode on Qwen 3.5, multiplying output tokens 5x–15x.',
          'First call after >5 min idle also includes cold-loading model weights into VRAM.',
        ],
        suggestedFixes: [
          'Switch to qwen2.5-coder:7b for instant grading, or pass `think: false` in Ollama options.',
          'Set OLLAMA_KEEP_ALIVE=30m to avoid repeated cold starts.',
        ],
      }
    }

    return {
      code: 'cold_load_or_vram_swap',
      severity: 'warn',
      title: `Slow local LLM response (${durationSec}s)`,
      summary: `Response succeeded but took ${durationSec}s${entry.model ? ` on ${entry.model}` : ''}.`,
      likelyCauses: [
        'Cold model load from SSD into GPU VRAM (first card after 5+ minutes idle or after switching models).',
        'Partial CPU offload because Chrome GPU process + other apps consumed VRAM.',
      ],
      suggestedFixes: [
        'Run `ollama ps` to verify 100% GPU placement (Processor column should say "100% GPU").',
        'Press Shift+Esc in Chrome to spot high-memory / GPU-heavy tabs.',
      ],
    }
  }

  return {
    code: 'ok',
    severity: 'info',
    title: `Completed in ${durationSec}s`,
    summary: `Healthy response latency${entry.model ? ` using ${entry.model}` : ''}.`,
    likelyCauses: [],
    suggestedFixes: [],
  }
}

export interface GradingStageInfo {
  phase: 'sending' | 'generating' | 'slow' | 'stalled'
  label: string
  hint: string
}

export function describeGradingStage(elapsedMs: number, model: string | null | undefined): GradingStageInfo {
  const modelLabel = model || 'local LLM'
  const sec = (elapsedMs / 1000).toFixed(1)
  const thinking = isThinkingModel(model)

  if (elapsedMs < 2_500) {
    return {
      phase: 'sending',
      label: `Sending answer to ${modelLabel}…`,
      hint: 'Waiting for first response from backend.',
    }
  }
  if (elapsedMs < SLOW_LLM_THRESHOLD_MS) {
    return {
      phase: 'generating',
      label: `Grading with ${modelLabel} (${sec}s)…`,
      hint: thinking
        ? 'Generating rubric feedback (Qwen 3.5 thinking tokens may add a few seconds).'
        : 'Evaluating answer against reference.',
    }
  }
  if (elapsedMs < VERY_SLOW_LLM_THRESHOLD_MS) {
    return {
      phase: 'slow',
      label: `Still waiting on ${modelLabel} (${sec}s)…`,
      hint: thinking
        ? 'Likely emitting hidden thinking tokens, cold-loading into VRAM, or spilling layers to CPU RAM.'
        : 'Likely cold-loading model weights into VRAM or spilling layers onto CPU RAM (check Chrome GPU memory).',
    }
  }
  return {
    phase: 'stalled',
    label: `Unusually slow (${sec}s) — ${modelLabel} may be stalled`,
    hint: 'Ollama may be swapping VRAM with Chrome or approaching a backend read timeout. You can Cancel, Inspect Diagnostics, or Show Answer.',
  }
}

export function startLlmTrace(params: {
  operation: string
  endpoint: string
  model?: string | null
}): string {
  const id = `llm-${Date.now().toString(36)}-${++seq}`
  const pendingCount = entries.filter((e) => e.status === 'pending').length + 1
  const entry: LlmTraceEntry = {
    id,
    operation: params.operation,
    endpoint: params.endpoint,
    model: params.model ?? null,
    startedAt: Date.now(),
    endedAt: null,
    durationMs: null,
    status: 'pending',
    httpStatus: null,
    errorMessage: null,
    rawDetail: null,
    responseModelUsed: null,
    degradedReason: null,
    chromeContext: captureChromeSnapshot(pendingCount),
    diagnosis: null,
  }
  entries = [entry, ...entries].slice(0, MAX_TRACE_ENTRIES)
  emit()
  return id
}

export function finishLlmTrace(
  id: string,
  outcome: {
    status: Exclude<LlmTraceStatus, 'pending'>
    httpStatus?: number | null
    errorMessage?: string | null
    rawDetail?: string | null
    responseModelUsed?: string | null
    degradedReason?: string | null
  },
): LlmTraceEntry | null {
  const idx = entries.findIndex((e) => e.id === id)
  if (idx === -1) return null

  const existing = entries[idx]
  const endedAt = Date.now()
  const durationMs = Math.max(0, endedAt - existing.startedAt)
  const effectiveStatus: LlmTraceStatus =
    outcome.status === 'ok' && durationMs >= SLOW_LLM_THRESHOLD_MS ? 'slow' : outcome.status

  const updated: LlmTraceEntry = {
    ...existing,
    endedAt,
    durationMs,
    status: effectiveStatus,
    httpStatus: outcome.httpStatus ?? existing.httpStatus,
    errorMessage: outcome.errorMessage ?? null,
    rawDetail: outcome.rawDetail ?? null,
    responseModelUsed: outcome.responseModelUsed ?? null,
    degradedReason: outcome.degradedReason ?? null,
    diagnosis: null,
  }
  updated.diagnosis = diagnoseLlmTrace(updated)

  const next = [...entries]
  next[idx] = updated
  entries = next
  emit()
  return updated
}

export function clearLlmTraces() {
  entries = entries.filter((e) => e.status === 'pending')
  emit()
}

export function getLlmTraceById(id: string | null | undefined): LlmTraceEntry | null {
  if (!id) return null
  return entries.find((e) => e.id === id) ?? null
}

export function getLlmTraceSnapshot(): LlmTraceSnapshot {
  return cachedSnapshot
}

export function subscribeLlmTraces(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useLlmTraces(): LlmTraceSnapshot {
  return useSyncExternalStore(subscribeLlmTraces, getLlmTraceSnapshot, getLlmTraceSnapshot)
}

export function buildDiagnosticReport(
  traceSnapshot: LlmTraceSnapshot,
  serverDiag: LlmDiagnosticsResponse | null,
  activeModel: string | null,
): string {
  const chrome = captureChromeSnapshot(traceSnapshot.activeCount)
  const payload = {
    generated_at: new Date().toISOString(),
    active_model: activeModel,
    browser: chrome,
    backend_diagnostics: serverDiag
      ? {
          backend_mode: serverDiag.backend_mode,
          ollama_reachable: serverDiag.ollama.reachable,
          ollama_version: serverDiag.ollama.version,
          ollama_latency_ms: serverDiag.ollama.latency_ms,
          ollama_error: serverDiag.ollama.error,
          loaded_models: serverDiag.ollama.loaded_models,
          host: serverDiag.host,
          hints: serverDiag.hints,
        }
      : 'unavailable (external backend or probe not run)',
    recent_client_traces: traceSnapshot.entries.slice(0, 12).map((e) => ({
      operation: e.operation,
      endpoint: e.endpoint,
      model: e.responseModelUsed || e.model,
      status: e.status,
      duration_ms: e.durationMs,
      http_status: e.httpStatus,
      error: e.errorMessage,
      diagnosis_code: e.diagnosis?.code ?? null,
      tab_visibility: e.chromeContext.visibilityState,
      in_flight_at_start: e.chromeContext.inFlightCount,
    })),
  }
  return JSON.stringify(payload, null, 2)
}

/** Test-only reset helper */
export function _resetLlmTracesForTest() {
  entries = []
  seq = 0
  emit()
}
