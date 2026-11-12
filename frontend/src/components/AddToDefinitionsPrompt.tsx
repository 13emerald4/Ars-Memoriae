import { looksLikeCodeTerm } from '../utils/lexiconExtractor'

export interface AddToDefinitionsPromptProps {
  term: string
  alreadyAdded?: boolean
  saving?: boolean
  onConfirm: () => void
  onDismiss?: () => void
  onViewList?: () => void
  compact?: boolean
  error?: string | null
}

/**
 * Shared confirmation banner asking the user whether to save an LLM-defined term
 * into the active card's persistent definitions list (Card Memory).
 */
export function AddToDefinitionsPrompt({
  term,
  alreadyAdded = false,
  saving = false,
  onConfirm,
  onDismiss,
  onViewList,
  compact = false,
  error,
}: AddToDefinitionsPromptProps) {
  const trimmed = (term || '').trim()
  const displayTerm = trimmed.length > 48 ? `${trimmed.slice(0, 45)}…` : trimmed

  if (alreadyAdded) {
    return (
      <div className="rounded-lg border border-emerald-500/35 bg-emerald-950/40 px-2.5 py-1.5 flex items-center justify-between gap-2 text-[11px] text-emerald-200">
        <span className="font-medium flex items-center gap-1.5 min-w-0 truncate">
          <span className="text-emerald-400 shrink-0">✓</span>
          <span className="truncate">Added to this card&apos;s definitions list</span>
        </span>
        {onViewList && (
          <button
            type="button"
            onClick={onViewList}
            className="shrink-0 text-[10px] font-semibold text-emerald-300 hover:text-emerald-100 underline cursor-pointer"
          >
            View list →
          </button>
        )}
      </div>
    )
  }

  return (
    <div
      className={`rounded-xl border border-sky-400/45 bg-sky-950/45 ${
        compact ? 'p-2 space-y-1.5' : 'p-2.5 space-y-2'
      } shadow-sm animate-in fade-in duration-150`}
    >
      <p className="text-xs font-medium text-sky-100 leading-snug">
        Would you like to add{' '}
        <span
          className={
            looksLikeCodeTerm(trimmed)
              ? 'font-mono text-emerald-300 font-semibold'
              : 'font-semibold text-white'
          }
          title={trimmed}
        >
          &ldquo;{displayTerm}&rdquo;
        </span>{' '}
        to this card&apos;s definitions list?
      </p>
      {error && <p className="text-[11px] text-rose-300">{error}</p>}
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={saving}
          onClick={onConfirm}
          className="flex-1 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 disabled:opacity-50 text-white px-2.5 py-1 text-[11px] font-semibold transition cursor-pointer shadow-sm"
        >
          {saving ? 'Adding…' : '✓ Yes, Add to Definitions'}
        </button>
        {onDismiss && (
          <button
            type="button"
            disabled={saving}
            onClick={onDismiss}
            className="rounded-lg border border-slate-700 bg-slate-900/70 hover:bg-slate-800 text-slate-300 px-2.5 py-1 text-[11px] font-medium transition cursor-pointer"
          >
            No thanks
          </button>
        )}
      </div>
    </div>
  )
}
