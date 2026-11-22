import { useEffect, useState } from 'react'
import { ApiError } from '../../api/client'
import {
  describeGradingStage,
  diagnoseLlmTrace,
  getLlmTraceById,
  isEmptyOllamaError,
  isThinkingModel,
  captureChromeSnapshot,
} from '../../utils/llmDiagnostics'

export interface LiveGradingStatusStripProps {
  activeModel: string
  startedAt: number | null
  onCancel: () => void
  onInspect: () => void
}

export function LiveGradingStatusStrip({
  activeModel,
  startedAt,
  onCancel,
  onInspect,
}: LiveGradingStatusStripProps) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!startedAt) return
    setNow(Date.now())
    const id = window.setInterval(() => setNow(Date.now()), 200)
    return () => window.clearInterval(id)
  }, [startedAt])

  const elapsedMs = startedAt ? Math.max(0, now - startedAt) : 0
  const stage = describeGradingStage(elapsedMs, activeModel)

  const toneClasses =
    stage.phase === 'stalled'
      ? 'border-rose-500/45 bg-rose-950/30 text-rose-100'
      : stage.phase === 'slow'
      ? 'border-amber-500/45 bg-amber-950/30 text-amber-100'
      : 'border-sky-500/35 bg-sky-950/25 text-sky-100'

  const spinnerClasses =
    stage.phase === 'stalled'
      ? 'border-rose-400/25 border-t-rose-300'
      : stage.phase === 'slow'
      ? 'border-amber-400/25 border-t-amber-300'
      : 'border-sky-400/25 border-t-sky-300'

  return (
    <div
      role="status"
      aria-live="polite"
      className={`mt-2.5 rounded-xl border px-3.5 py-2.5 text-xs transition-colors ${toneClasses}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            aria-hidden="true"
            className={`h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 ${spinnerClasses}`}
          />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{stage.label}</span>
              <span className="rounded border border-current/25 bg-black/25 px-1.5 py-0.2 font-mono text-[0.6875rem] tabular-nums">
                {(elapsedMs / 1000).toFixed(1)}s
              </span>
            </div>
            <p className="mt-0.5 text-[0.6875rem] opacity-85 leading-relaxed">{stage.hint}</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={onInspect}
            className="btn text-[0.6875rem] py-1 px-2 border-current/30 bg-black/20 hover:bg-black/40"
          >
            Inspect
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="btn text-[0.6875rem] py-1 px-2 border-current/35 bg-black/25 hover:bg-black/45 font-medium"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export interface LlmErrorDiagnosticBannerProps {
  error: unknown
  activeModel: string
  canRetry?: boolean
  canReveal?: boolean
  onRetry?: () => void
  onSwitchAndRetry?: (model: string) => void
  onReveal?: () => void
  onInspect: (traceId?: string | null) => void
  onDismiss?: () => void
}

export function LlmErrorDiagnosticBanner({
  error,
  activeModel,
  canRetry = false,
  canReveal = false,
  onRetry,
  onSwitchAndRetry,
  onReveal,
  onInspect,
  onDismiss,
}: LlmErrorDiagnosticBannerProps) {
  if (!error) return null

  const rawMessage = error instanceof Error ? error.message : String(error)
  const apiErr = error instanceof ApiError ? error : null
  const trace = apiErr?.traceId ? getLlmTraceById(apiErr.traceId) : null

  const looksLikeLlmError =
    Boolean(trace) ||
    /ollama|llm|model|timeout|timed out|generation failed|failed to fetch|vram/i.test(rawMessage)

  const diagnosis =
    trace?.diagnosis ??
    (looksLikeLlmError
      ? diagnoseLlmTrace({
          model: activeModel,
          durationMs: apiErr?.durationMs ?? 0,
          status: apiErr?.status === 504 || apiErr?.status === 408 ? 'timeout' : 'error',
          httpStatus: apiErr?.status ?? null,
          errorMessage: rawMessage,
          rawDetail: rawMessage,
          degradedReason: null,
          chromeContext: captureChromeSnapshot(0),
        })
      : null)

  const durationSec =
    trace?.durationMs != null
      ? `${(trace.durationMs / 1000).toFixed(1)}s`
      : apiErr?.durationMs != null
      ? `${(apiErr.durationMs / 1000).toFixed(1)}s`
      : null

  const httpStatus = trace?.httpStatus ?? apiErr?.status ?? null
  const modelLabel = trace?.responseModelUsed || trace?.model || (looksLikeLlmError ? activeModel : null)
  const emptyOllama = isEmptyOllamaError(rawMessage)
  const offerFastSwitch =
    looksLikeLlmError &&
    Boolean(onSwitchAndRetry) &&
    isThinkingModel(modelLabel || activeModel)

  return (
    <div
      role="alert"
      className="rounded-xl border border-rose-500/45 bg-rose-950/35 px-4 py-3 text-sm text-rose-100 space-y-2.5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-rose-100 break-words">
              {rawMessage || 'Local LLM request failed'}
            </span>
            {emptyOllama && (
              <span className="rounded border border-amber-500/40 bg-amber-500/15 px-1.5 py-0.5 text-[0.6875rem] font-medium text-amber-200">
                Empty backend timeout/drop
              </span>
            )}
            {httpStatus != null && (
              <span className="rounded border border-rose-400/30 bg-black/30 px-1.5 py-0.5 font-mono text-[0.6875rem] text-rose-200">
                HTTP {httpStatus}
              </span>
            )}
            {durationSec && (
              <span className="rounded border border-rose-400/30 bg-black/30 px-1.5 py-0.5 font-mono text-[0.6875rem] text-rose-200">
                {durationSec}
              </span>
            )}
            {modelLabel && (
              <span className="rounded border border-slate-700 bg-slate-900/80 px-1.5 py-0.5 font-mono text-[0.6875rem] text-slate-300">
                {modelLabel}
              </span>
            )}
          </div>

          {diagnosis && (
            <p className="text-xs text-rose-200/90 leading-relaxed">
              <strong className="font-semibold text-rose-100">{diagnosis.title}:</strong>{' '}
              {diagnosis.summary}
            </p>
          )}
        </div>

        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="shrink-0 rounded p-1 text-rose-300/75 hover:bg-rose-500/20 hover:text-rose-100 leading-none"
          >
            &times;
          </button>
        )}
      </div>

      {looksLikeLlmError && (
        <div className="flex flex-wrap items-center gap-2 pt-0.5">
          {canRetry && onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="btn text-xs py-1 px-2.5 border-rose-400/40 bg-rose-500/20 hover:bg-rose-500/30 text-rose-100 font-medium"
            >
              ↻ Retry Grading
            </button>
          )}
          {offerFastSwitch && onSwitchAndRetry && (
            <button
              type="button"
              onClick={() => onSwitchAndRetry('qwen2.5-coder:7b')}
              className="btn text-xs py-1 px-2.5 border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-200 font-medium"
            >
              Switch to qwen2.5-coder:7b &amp; Retry
            </button>
          )}
          {canReveal && onReveal && (
            <button
              type="button"
              onClick={onReveal}
              className="btn text-xs py-1 px-2.5 border-slate-600 bg-slate-900/80 hover:bg-slate-800 text-slate-200"
            >
              Show Answer Instead
            </button>
          )}
          <button
            type="button"
            onClick={() => onInspect(apiErr?.traceId ?? null)}
            className="btn text-xs py-1 px-2.5 border-sky-500/40 bg-sky-500/15 hover:bg-sky-500/25 text-sky-200 font-medium"
          >
            Inspect LLM Diagnostics
          </button>
        </div>
      )}
    </div>
  )
}
