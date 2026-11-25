import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { SubmitAnswerResponse, VramMetrics } from '../../api/types'
import { getModelDisplayInfo, isAllowedGradingModel, isAntigravityModel } from '../../api/types'

const LOCAL_MODEL_OPTIONS = ['qwen3.5:9b', 'qwen2.5-coder:7b', 'qwen3.5:4b'] as const

export interface VramConstraintPromptProps {
  result: SubmitAnswerResponse
  loading: boolean
  onSwitchModel: (model: string) => void
  onRetry: () => void
  onGradeManually: () => void
}

export function VramConstraintPrompt({
  result,
  loading,
  onSwitchModel,
  onRetry,
  onGradeManually,
}: VramConstraintPromptProps) {
  const defaultModel =
    result.fallback_model ||
    result.available_fallback_models?.[0] ||
    'qwen2.5-coder:1.5b'
  const [chosenModel, setChosenModel] = useState<string>(defaultModel)

  return (
    <div className="rounded-xl border border-amber-500/50 bg-amber-950/40 p-5 space-y-4 text-slate-200 shadow-xl animate-fadeIn">
      <div className="flex items-start gap-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30">
          <svg className="w-5 h-5 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-amber-200">
              GPU VRAM / Memory Limit Reached
            </h4>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">
              {result.failed_model || 'Local Model'}
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Your system's available GPU VRAM or host memory could not allocate space for{' '}
            <strong className="text-amber-300 font-mono">{result.failed_model || 'this model'}</strong>.
            Would you like to switch to a smaller local model, or free up more VRAM by closing apps and retry?
          </p>
        </div>
      </div>

      <div className="rounded-lg bg-black/40 border border-white/10 p-3.5 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="space-y-1">
            <span className="text-slate-400 font-medium">Recommended next biggest model:</span>
            <div className="flex items-center gap-2 font-mono text-emerald-300 font-semibold text-sm">
              <span>{chosenModel}</span>
              <span className="chip text-[0.625rem] px-1.5 py-0.2 border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
                {getModelInfo(chosenModel).badge || 'Smaller size'}
              </span>
            </div>
          </div>

          {result.available_fallback_models &&
            result.available_fallback_models.filter(isAllowedGradingModel).length > 1 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Other models:</span>
                <select aria-label="Grading model"
                  value={chosenModel}
                  onChange={(e) => setChosenModel(e.target.value)}
                  className="select text-xs py-1 px-2.5 bg-slate-900 border-slate-700 text-slate-200 font-mono rounded"
                >
                  {result.available_fallback_models.filter(isAllowedGradingModel).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2.5 pt-1">
        <button
          type="button"
          disabled={loading}
          onClick={() => onSwitchModel(chosenModel)}
          className="btn btn-primary text-xs py-2 px-4 font-medium flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 text-white border-emerald-500 shadow-sm"
        >
          {loading ? (
            <>
              <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
              <span>Grading with {chosenModel}…</span>
            </>
          ) : (
            <>
              <span>Switch to {chosenModel} & Grade</span>
            </>
          )}
        </button>

        <button
          type="button"
          disabled={loading}
          onClick={onRetry}
          className="btn btn-secondary text-xs py-2 px-3.5 flex items-center gap-1.5 border-slate-700 hover:bg-slate-800 text-slate-200"
          title="Retry AI model"
        >
          <span>↻ Retry {result.failed_model || 'Grading'}</span>
        </button>

        <button
          type="button"
          disabled={loading}
          onClick={onGradeManually}
          className="btn text-xs py-2 px-3 opacity-75 hover:opacity-100 text-slate-400 hover:text-slate-200 ml-auto"
        >
          <span>Grade Manually</span>
        </button>
      </div>
    </div>
  )
}

/** Model metadata formatter for Antigravity subscription and local Ollama models */
export function getModelInfo(modelName: string): {
  label: string
  short: string
  archetype: string
  badge?: string
  desc?: string
  provider: 'ollama' | 'antigravity'
} {
  return getModelDisplayInfo(modelName)
}

export interface DiscreteModelSelectorProps {
  activeModel: string
  installedModels: string[]
  grading: boolean
  hasAnswer: boolean
  isRevealed?: boolean
  onSelectModel: (model: string) => void
  onGradeWithModel: (model: string) => void
  onModelsUpdated?: (models: string[]) => void
  onOpenDiagnostics?: () => void
  hasRecentIssue?: boolean
  className?: string
}

/** Discrete model switcher positioned adjacent to grading button.
 *  Allows switching between the local Ollama grading model archetypes.
 */
export function DiscreteModelSelector({
  activeModel,
  installedModels,
  grading,
  hasAnswer,
  isRevealed = false,
  onSelectModel,
  onGradeWithModel,
  onModelsUpdated,
  onOpenDiagnostics,
  hasRecentIssue = false,
  className = '',
}: DiscreteModelSelectorProps) {
  const [open, setOpen] = useState(false)
  const [vram, setVram] = useState<VramMetrics | null>(null)
  const [pullingModel, setPullingModel] = useState<string | null>(null)
  const [pullError, setPullError] = useState<string | null>(null)
  const [extraInstalled, setExtraInstalled] = useState<string[]>([])
  const menuRef = useRef<HTMLDivElement>(null)
  const isAgyActive = isAntigravityModel(activeModel)

  const effectiveInstalled =
    extraInstalled.length > 0
      ? Array.from(new Set([...installedModels, ...extraInstalled]))
      : installedModels

  const handlePullModel = async (modelToPull: string) => {
    if (pullingModel) return
    setPullError(null)
    setPullingModel(modelToPull)
    try {
      const res = await api.pullModel(modelToPull)
      if (res.models_installed && res.models_installed.length > 0) {
        setExtraInstalled(res.models_installed)
        onModelsUpdated?.(res.models_installed)
      } else {
        setExtraInstalled((prev) => Array.from(new Set([...prev, modelToPull])))
      }
      onSelectModel(modelToPull)
    } catch (err) {
      setPullError(err instanceof Error ? err.message : `Failed to pull ${modelToPull}`)
    } finally {
      setPullingModel(null)
    }
  }

  useEffect(() => {
    if (!open) return
    if (isAgyActive) {
      setVram(null)
    } else {
      api.vramStatus(activeModel).then(setVram).catch(() => {})
    }
    const handleDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handleDown)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleDown)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open, activeModel, isAgyActive])

  const models = LOCAL_MODEL_OPTIONS

  const currentInfo = getModelInfo(activeModel)
  const isFast = currentInfo.badge?.toLowerCase().includes('fast') || currentInfo.badge?.toLowerCase().includes('speed')

  return (
    <div className={`relative inline-block ${className}`} ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={`group flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all ${
          open
            ? 'border-sky-500/60 bg-sky-950/50 text-sky-200 ring-2 ring-sky-500/20'
            : grading
            ? 'border-amber-500/40 bg-amber-500/10 text-amber-200 hover:border-amber-400'
            : 'border-slate-700/80 bg-slate-900/80 text-slate-300 hover:border-slate-500 hover:bg-slate-800 hover:text-white'
        }`}
        title={`Model: ${activeModel}`}
      >
        <span className="text-[0.625rem] font-mono text-slate-400 uppercase">
          {isAgyActive ? 'AGY' : isFast ? 'Fast' : 'AI'}
        </span>
        <span className="font-mono text-[0.6875rem] font-semibold tracking-tight">{currentInfo.short}</span>
        {hasRecentIssue && !grading && (
          <span
            className="h-1.5 w-1.5 rounded-full bg-amber-400"
            title="Recent slow or failed local LLM call — click to inspect diagnostics"
          />
        )}
        <span
          className={`text-[0.5625rem] text-slate-400 transition-transform duration-150 ${
            open ? 'rotate-180 text-sky-400' : 'group-hover:text-slate-200'
          }`}
        >
          ▾
        </span>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-88 rounded-xl border border-slate-700/80 bg-slate-900/95 p-3 shadow-2xl backdrop-blur-md z-50 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-slate-100">AI Grading Engine</span>
              <span className="text-[0.625rem] text-slate-400 font-mono">Local Ollama</span>
            </div>
            <span className="flex items-center gap-1 text-[0.625rem] text-emerald-400 font-medium">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {isAgyActive ? 'Subscription' : 'Quantized'}
            </span>
          </div>

          {/* Live VRAM Telemetry inside Discrete Switcher (Ollama only) */}
          {!isAgyActive && vram && (
            <div className="my-2 rounded-lg border border-slate-800 bg-slate-950/80 p-2 space-y-1.5">
              <div className="flex items-center justify-between text-[0.6875rem]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <svg className="w-3 h-3 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                  <span>VRAM Hardware Telemetry</span>
                </span>
                <span className="text-[0.625rem] font-mono text-slate-400 truncate max-w-[140px]">{vram.gpu_name}</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
                <div className="rounded bg-slate-900/80 p-1 border border-slate-800/60">
                  <div className="text-[0.5625rem] uppercase text-slate-400">Capacity</div>
                  <div className="font-bold text-slate-100 text-[0.6875rem]">
                    {vram.capacity_gb != null ? `${vram.capacity_gb.toFixed(1)} GB` : 'N/A'}
                  </div>
                </div>
                <div className="rounded bg-sky-950/40 p-1 border border-sky-500/30">
                  <div className="text-[0.5625rem] uppercase text-sky-300">Model VRAM</div>
                  <div className="font-bold text-sky-200 text-[0.6875rem]">
                    {vram.model_loaded && vram.model_vram_gb
                      ? `${vram.model_vram_gb.toFixed(1)} GB`
                      : `~${vram.model_approx_gb || 0} GB`}
                  </div>
                </div>
                <div className="rounded bg-emerald-950/40 p-1 border border-emerald-500/30">
                  <div className="text-[0.5625rem] uppercase text-emerald-300">Available</div>
                  <div className="font-bold text-emerald-200 text-[0.6875rem]">
                    {vram.available_gb != null ? `${vram.available_gb.toFixed(1)} GB` : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="my-2 space-y-1.5 max-h-64 overflow-y-auto pr-1">
            {models.map((m) => {
              const isAgyItem = isAntigravityModel(m)
              const activeLower = (activeModel || '').toLowerCase()
              const mLower = m.toLowerCase()
              const isCurrent = isAgyItem
                ? mLower === activeLower
                : activeLower === mLower || activeLower.startsWith(`${mLower}-`)
              const info = getModelInfo(m)
              const isInstalled = effectiveInstalled.some(
                (im) =>
                  im.toLowerCase() === mLower ||
                  (!isAgyItem && im.toLowerCase().startsWith(mLower)),
              )
              const isSelectable = isInstalled || isAgyItem
              const isPulling = pullingModel === m
              return (
                <div
                  key={m}
                  className={`group flex items-center justify-between rounded-lg border p-2 transition ${
                    isCurrent
                      ? 'border-sky-500/60 bg-sky-950/40 text-sky-100 ring-1 ring-sky-500/30'
                      : isSelectable
                      ? 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-800/60 text-slate-300 cursor-pointer'
                      : 'border-slate-800/60 bg-slate-900/20 text-slate-500'
                  }`}
                  onClick={() => {
                    if (isSelectable) {
                      onSelectModel(m)
                      setOpen(false)
                    } else if (!pullingModel) {
                      void handlePullModel(m)
                    }
                  }}
                >
                  <div className="flex-1 min-w-0 pr-2">
                    <div className="flex items-center gap-1.5">
                      <span className={`font-semibold truncate ${isSelectable ? 'text-slate-100' : 'text-slate-400'}`}>
                        {info.label}
                      </span>
                      {info.badge && (
                        <span
                          className={`text-[0.5625rem] px-1 py-0.2 rounded font-semibold border ${
                            info.provider === 'antigravity'
                              ? 'border-indigo-400/40 text-indigo-200 bg-indigo-500/15'
                              : info.badge.includes('Speed') || info.badge.includes('Fast')
                              ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'
                              : info.badge.includes('Technical')
                              ? 'border-indigo-500/40 text-indigo-300 bg-indigo-500/10'
                              : 'border-sky-500/40 text-sky-300 bg-sky-500/10'
                          }`}
                        >
                          {info.badge}
                        </span>
                      )}
                      {isCurrent && (
                        <div className="ml-auto shrink-0 text-right leading-tight">
                          <div className="text-[0.625rem] text-sky-400 font-bold">Active</div>
                          {vram && (
                            <div className="text-[0.5625rem] font-mono text-sky-200/80">
                              {vram.model_loaded && vram.model_vram_gb
                                ? `Using ${vram.model_vram_gb.toFixed(1)} GB VRAM`
                                : '0 GB in VRAM'}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="text-[0.625rem] font-medium italic text-sky-300/90 mt-0.5">
                      {info.archetype}
                    </div>
                    {info.desc && (
                      <p className="text-[0.625rem] text-slate-400 truncate mt-0.5">{info.desc}</p>
                    )}
                  </div>

                  {/* Immediate Action: Grade if selectable, or Pull button if local model missing */}
                  {isSelectable ? (
                    hasAnswer && (
                      <button
                        type="button"
                        className="shrink-0 rounded px-2 py-1 text-[0.6875rem] font-medium border border-slate-700 bg-slate-800 hover:border-sky-500 hover:bg-sky-600 hover:text-white text-slate-200 transition"
                        title={`Grade answer now using ${info.label}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          onGradeWithModel(m)
                          setOpen(false)
                        }}
                      >
                        {grading ? '↻ Retry' : isRevealed ? '↻ Re-grade' : 'Grade'}
                      </button>
                    )
                  ) : (
                    <button
                      type="button"
                      disabled={Boolean(pullingModel)}
                      className="shrink-0 rounded px-2 py-1 text-[0.625rem] font-mono border border-sky-500/40 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20 hover:text-sky-100 disabled:opacity-50 cursor-pointer transition"
                      onClick={(e) => {
                        e.stopPropagation()
                        void handlePullModel(m)
                      }}
                      title={`Download ${m} via Ollama`}
                    >
                      {isPulling ? 'Pulling…' : 'Pull'}
                    </button>
                  )}
                </div>
              )
            })}
          </div>

          {pullError && (
            <div className="mb-2 rounded border border-rose-500/40 bg-rose-950/50 px-2 py-1.5 text-[0.625rem] text-rose-200">
              {pullError}
            </div>
          )}

          <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2 text-[0.6875rem]">
            <span className="text-slate-400">
              {pullingModel ? (
                <span className="text-sky-300 flex items-center gap-1">
                  <span className="animate-spin text-xs">↻</span> Downloading {pullingModel}…
                </span>
              ) : grading ? (
                <span className="text-amber-300 flex items-center gap-1">
                  <span className="animate-spin text-xs">↻</span> Grading in progress…
                </span>
              ) : hasAnswer ? (
                <span>Click model to switch, or button to grade</span>
              ) : (
                <span>Click model to set as active grader</span>
              )}
            </span>
            <div className="flex items-center gap-2.5 ml-auto">
              {onOpenDiagnostics && (
                <button
                  type="button"
                  className={`underline font-medium cursor-pointer ${
                    hasRecentIssue
                      ? 'text-amber-300 hover:text-amber-100'
                      : 'text-sky-400 hover:text-sky-200'
                  }`}
                  onClick={() => {
                    setOpen(false)
                    onOpenDiagnostics()
                  }}
                >
                  {hasRecentIssue ? 'Inspect slow/failed LLM' : 'LLM Diagnostics'}
                </button>
              )}
              {grading && (
                <button
                  type="button"
                  className="text-amber-400 hover:text-amber-200 underline font-medium cursor-pointer"
                  onClick={() => {
                    const alt = models.find((m) => m !== activeModel) || activeModel
                    onGradeWithModel(alt)
                    setOpen(false)
                  }}
                >
                  Cancel &amp; retry
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
